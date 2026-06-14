# -*- coding: utf-8 -*-
"""Authentication module: password hashing, JWT tokens, and FastAPI middleware.

Login is disabled by default and only enabled when the environment
variable ``QWENPAW_AUTH_ENABLED`` is set to a truthy value (``true``,
``1``, ``yes``).  Credentials are created through a web-based
registration flow rather than environment variables, so that agents
running inside the process cannot read plaintext passwords.

Multi-user design: the first registered account becomes an administrator.
Additional users can be managed through the authenticated user-management
API.  Legacy single-user ``auth.json`` files are migrated in place.

Uses only Python stdlib (hashlib, hmac, secrets) to avoid adding new
dependencies.  The password is stored as a salted SHA-256 hash in
``auth.json`` under ``SECRET_DIR``.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..constant import SECRET_DIR, EnvVarLoader
from ..security.secret_store import (
    AUTH_SECRET_FIELDS,
    decrypt_dict_fields,
    encrypt_dict_fields,
    is_encrypted,
)
from qwenpaw_ext.nexora import db

logger = logging.getLogger(__name__)

AUTH_FILE = SECRET_DIR / "auth.json"

# Token validity: 7 days (default)
TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600

# Maximum token validity: 100 years (for "permanent" tokens)
TOKEN_EXPIRY_MAX = 100 * 365 * 24 * 3600

# Paths that do NOT require authentication
_PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/api/auth/login",
        "/api/auth/status",
        "/api/auth/register",
        "/api/version",
        "/api/settings/language",
        "/api/frontend_plugin",
    },
)

# Prefixes that do NOT require authentication (static assets)
# /api/frontend_plugin/ is safe: only read-only GET handlers are registered
# under that prefix (list + static file serving).  All write operations
# remain under /api/plugins/ which requires authentication.
_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/assets/",
    "/logo.png",
    "/qwenpaw-symbol.svg",
    "/api/frontend_plugin/",
)

_MUTATING_METHODS: frozenset[str] = frozenset(
    {"POST", "PUT", "PATCH", "DELETE"},
)

_AUDIT_SKIP_PREFIXES: tuple[str, ...] = (
    "/api/nexora/audit",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/status",
    "/api/auth/verify",
)

_API_PERMISSION_PREFIXES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("MUTATE", "users.manage", ("/api/auth/users", "/api/auth/roles")),
    (
        "*",
        "users.view",
        ("/api/auth/users", "/api/auth/roles", "/api/auth/permissions"),
    ),
    ("*", "models.manage", ("/api/local-models",)),
    ("MUTATE", "models.manage", ("/api/models",)),
    ("*", "mcp.manage", ("/api/mcp",)),
    ("*", "tools.manage", ("/api/tools",)),
    ("MUTATE", "agents.manage", ("/api/agents",)),
    ("*", "agents.use", ("/api/agents",)),
    ("MUTATE", "agents.manage", ("/api/workspace",)),
    ("*", "agents.use", ("/api/workspace",)),
    ("*", "agents.manage", ("/api/config", "/api/envs")),
    ("*", "system.admin", ("/api/plugins", "/api/backups")),
    ("*", "system.admin", ("/api/settings",)),
    ("*", "system.admin", ("/api/plan",)),
    ("*", "agents.manage", ("/api/cron",)),
    ("*", "system.admin", ("/api/security",)),
    ("*", "audit.view", ("/api/token-usage", "/api/agent-stats")),
    ("*", "agents.use", ("/api/console", "/api/chats", "/api/messages")),
    ("*", "agents.use", ("/api/files", "/api/skills")),
)

DEFAULT_PERMISSIONS: tuple[str, ...] = (
    "system.admin",
    "users.manage",
    "users.view",
    "agents.manage",
    "agents.use",
    "tools.manage",
    "tools.execute",
    "models.manage",
    "mcp.manage",
    "audit.view",
)

PERMISSION_IMPLICATIONS: dict[str, tuple[str, ...]] = {
    "users.view": ("users.manage",),
    "agents.use": ("agents.manage",),
    "tools.execute": ("tools.manage",),
}

ROLE_DEFINITIONS: dict[str, dict] = {
    "admin": {
        "name": "平台管理员",
        "permissions": list(DEFAULT_PERMISSIONS),
    },
    "operator": {
        "name": "平台操作员",
        "permissions": [
            "agents.manage",
            "agents.use",
            "tools.manage",
            "tools.execute",
            "mcp.manage",
        ],
    },
}


def _default_roles() -> dict[str, dict]:
    from qwenpaw_ext.nexora.rbac import default_roles

    return default_roles()


# ---------------------------------------------------------------------------
# Helpers (reuse SECRET_DIR patterns from envs/store.py)
# ---------------------------------------------------------------------------


def _chmod_best_effort(path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _prepare_secret_parent(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod_best_effort(path.parent, 0o700)


# ---------------------------------------------------------------------------
# Password hashing (salted SHA-256, no external deps)
# ---------------------------------------------------------------------------


def _hash_password(
    password: str,
    salt: Optional[str] = None,
) -> tuple[str, str]:
    """Hash *password* with *salt*.  Returns ``(hash_hex, salt_hex)``."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return h, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify *password* against a stored hash."""
    h, _ = _hash_password(password, salt)
    return hmac.compare_digest(h, stored_hash)


# ---------------------------------------------------------------------------
# Token generation / verification (HMAC-SHA256, no PyJWT needed)
# ---------------------------------------------------------------------------


def _get_jwt_secret() -> str:
    """Return the signing secret, creating one if absent."""
    data = _load_auth_data()
    secret = data.get("jwt_secret", "")
    if not secret:
        secret = secrets.token_hex(32)
        data["jwt_secret"] = secret
        _save_auth_data(data)
    return secret


def create_token(username: str, expiry_seconds: Optional[int] = None) -> str:
    """Create an HMAC-signed token: ``base64(payload).signature``.

    Args:
        username: The username to encode in the token.
        expiry_seconds: Custom expiry time in seconds.
            Use -1 or 0 for permanent tokens.
            Defaults to TOKEN_EXPIRY_SECONDS (7 days).
    """
    import base64

    if expiry_seconds is None:
        expiry_seconds = TOKEN_EXPIRY_SECONDS
    elif expiry_seconds <= 0:
        # Permanent token: 100 years
        expiry_seconds = TOKEN_EXPIRY_MAX
    else:
        # Cap at maximum allowed expiry
        expiry_seconds = min(expiry_seconds, TOKEN_EXPIRY_MAX)

    secret = _get_jwt_secret()
    # Generate unique token ID (jti) for revocation support
    token_id = secrets.token_hex(16)
    payload = json.dumps(
        {
            "sub": username,
            "exp": int(time.time()) + expiry_seconds,
            "iat": int(time.time()),
            "jti": token_id,  # JWT ID for individual revocation
        },
    )
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(
        secret.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token(token: str) -> Optional[str]:
    """Verify *token*, return username if valid, ``None`` otherwise.

    Also checks if the token has been revoked (appears in the revocation list).
    """
    import base64

    try:
        parts = token.split(".", 1)
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        secret = _get_jwt_secret()
        expected_sig = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None

        # Check if token is revoked
        jti = payload.get("jti")
        if jti and _is_token_revoked(jti):
            return None

        username = payload.get("sub")
        if not username:
            return None
        data = _load_normalized_auth_data()
        _, user = _find_user(data, username)
        if not user or user.get("status") != "active":
            return None
        return username
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        logger.debug("Token verification failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Auth data persistence (auth.json in SECRET_DIR)
# ---------------------------------------------------------------------------


def _load_auth_data() -> dict:
    """Load ``auth.json`` from ``SECRET_DIR``.

    Returns the parsed dict, or a sentinel with ``_auth_load_error``
    set to ``True`` when the file exists but cannot be read/parsed so
    that callers can fail closed instead of silently bypassing auth.

    Encrypted fields (``jwt_secret``) are transparently decrypted.
    Legacy plaintext values trigger an automatic re-encryption.
    """
    if AUTH_FILE.is_file():
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            needs_rewrite = any(
                isinstance(data.get(field), str)
                and data.get(field)
                and not is_encrypted(data[field])
                for field in AUTH_SECRET_FIELDS
            )
            data = decrypt_dict_fields(data, AUTH_SECRET_FIELDS)
            if needs_rewrite:
                try:
                    _save_auth_data(data)
                except Exception as enc_err:
                    logger.debug(
                        "Deferred plaintext→encrypted migration for"
                        " auth.json: %s",
                        enc_err,
                    )
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load auth file %s: %s", AUTH_FILE, exc)
            return {"_auth_load_error": True}
    return {}


def _save_auth_file(data: dict) -> None:
    """Save file-backed auth metadata with restrictive permissions."""
    _prepare_secret_parent(AUTH_FILE)
    encrypted_data = encrypt_dict_fields(data, AUTH_SECRET_FIELDS)
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(encrypted_data, f, indent=2, ensure_ascii=False)
    _chmod_best_effort(AUTH_FILE, 0o600)


def _has_identity_payload(data: dict) -> bool:
    return "users" in data or "roles" in data


def _has_file_secret_payload(data: dict) -> bool:
    file_keys = set(AUTH_SECRET_FIELDS) | {
        "revoked_tokens",
        "revoked_tokens_meta",
    }
    return any(key in data for key in file_keys)


def _save_auth_data(data: dict) -> None:
    """Persist auth data.

    When PostgreSQL is enabled, user/role identity data is stored in the DB.
    JWT secrets and token revocation metadata remain file-backed for this
    phase so existing token handling stays compatible.
    """
    if db.is_database_enabled():
        if _has_identity_payload(data):
            from qwenpaw_ext.nexora.repositories import auth_postgres

            auth_postgres.save_auth_data(data)
        if not _has_file_secret_payload(data):
            return

        file_data = _load_auth_data()
        if file_data.get("_auth_load_error"):
            file_data = {}
        for key in set(AUTH_SECRET_FIELDS) | {
            "revoked_tokens",
            "revoked_tokens_meta",
        }:
            if key in data:
                file_data[key] = data[key]
        _save_auth_file(file_data)
        return

    _save_auth_file(data)


def _now() -> int:
    return int(time.time())


def _public_user(user: dict) -> dict:
    return {
        "id": user.get("id", ""),
        "username": user.get("username", ""),
        "roles": list(user.get("roles") or []),
        "status": user.get("status", "active"),
        "created_at": user.get("created_at", 0),
        "updated_at": user.get("updated_at", 0),
    }


def _normalize_auth_data(data: dict) -> dict:
    """Migrate legacy single-user auth data to the multi-user schema."""
    if data.get("_auth_load_error"):
        return data

    users = data.get("users")
    if isinstance(users, list):
        pass
    else:
        legacy_user = data.get("user")
        if isinstance(legacy_user, dict) and legacy_user.get("username"):
            ts = _now()
            data["users"] = [
                {
                    "id": legacy_user.get("id") or secrets.token_hex(8),
                    "username": legacy_user.get("username", ""),
                    "password_hash": legacy_user.get("password_hash", ""),
                    "password_salt": legacy_user.get("password_salt", ""),
                    "roles": legacy_user.get("roles") or ["admin"],
                    "status": legacy_user.get("status") or "active",
                    "created_at": legacy_user.get("created_at") or ts,
                    "updated_at": legacy_user.get("updated_at") or ts,
                },
            ]
            _save_auth_data(data)
        else:
            data["users"] = []
    if not isinstance(data.get("roles"), dict):
        data["roles"] = _default_roles()
        _save_auth_data(data)
    else:
        changed = False
        roles = data["roles"]
        for role_id, role in _default_roles().items():
            if role_id not in roles:
                roles[role_id] = role
                changed = True
            else:
                existing_permissions = list(
                    roles[role_id].get("permissions") or [],
                )
                merged_permissions = list(
                    dict.fromkeys(
                        [*existing_permissions, *role.get("permissions", [])],
                    ),
                )
                if merged_permissions != existing_permissions:
                    roles[role_id]["permissions"] = merged_permissions
                    changed = True
                roles[role_id]["builtin"] = True
                changed = True
        if changed:
            data["roles"] = roles
            _save_auth_data(data)
    return data


def _normalize_db_auth_data(data: dict) -> dict:
    if data.get("_auth_load_error"):
        return data

    changed = False
    if not isinstance(data.get("users"), list):
        data["users"] = []
        changed = True

    roles = data.get("roles")
    if not isinstance(roles, dict):
        data["roles"] = _default_roles()
        changed = True
    else:
        for role_id, role in _default_roles().items():
            if role_id not in roles:
                roles[role_id] = role
                changed = True
                continue
            existing_permissions = list(
                roles[role_id].get("permissions") or [],
            )
            merged_permissions = list(
                dict.fromkeys(
                    [*existing_permissions, *role.get("permissions", [])],
                ),
            )
            if merged_permissions != existing_permissions:
                roles[role_id]["permissions"] = merged_permissions
                changed = True
            if not roles[role_id].get("builtin"):
                roles[role_id]["builtin"] = True
                changed = True
        data["roles"] = roles

    if changed:
        from qwenpaw_ext.nexora.repositories import auth_postgres

        auth_postgres.save_auth_data(data)
    return data


def _load_normalized_auth_data() -> dict:
    if db.is_database_enabled():
        from qwenpaw_ext.nexora.repositories import auth_postgres

        return _normalize_db_auth_data(auth_postgres.load_auth_data())
    return _normalize_auth_data(_load_auth_data())


def _find_user(data: dict, username: str) -> tuple[int, dict | None]:
    for idx, user in enumerate(data.get("users", [])):
        if user.get("username") == username:
            return idx, user
    return -1, None


def _role_permissions(role_ids: list[str]) -> set[str]:
    data = _load_normalized_auth_data()
    roles = data.get("roles") or _default_roles()
    permissions: set[str] = set()
    for role_id in role_ids:
        role = roles.get(role_id)
        if role:
            permissions.update(role["permissions"])
    return permissions


def user_has_permission(username: str, permission: str) -> bool:
    data = _load_normalized_auth_data()
    _, user = _find_user(data, username)
    if not user or user.get("status") != "active":
        return False
    roles = list(user.get("roles") or [])
    if "admin" in roles:
        return True
    permissions = _role_permissions(roles)
    return permission in permissions or any(
        implied_by in permissions
        for implied_by in PERMISSION_IMPLICATIONS.get(permission, ())
    )


def require_permission(username: str, permission: str) -> None:
    if not user_has_permission(username, permission):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Permission denied")


def list_roles() -> list[dict]:
    data = _load_normalized_auth_data()
    roles = data.get("roles") or _default_roles()
    return [
        {
            "id": role_id,
            "name": role.get("name", role_id),
            "description": role.get("description", ""),
            "permissions": list(role.get("permissions") or []),
            "builtin": bool(role.get("builtin", False)),
        }
        for role_id, role in roles.items()
    ]


def list_permissions() -> list[str]:
    return list(DEFAULT_PERMISSIONS)


def _role_exists(data: dict, role_id: str) -> bool:
    roles = data.get("roles") or _default_roles()
    return role_id in roles


def _valid_role_ids(data: dict, role_ids: list[str]) -> list[str]:
    return [role_id for role_id in role_ids if _role_exists(data, role_id)]


def create_role(
    role_id: str,
    name: str,
    permissions: list[str],
    description: str = "",
) -> dict | None:
    data = _load_normalized_auth_data()
    role_id = role_id.strip()
    if not role_id or not name.strip():
        return None
    if role_id in (data.get("roles") or {}):
        return None
    allowed_permissions = set(DEFAULT_PERMISSIONS)
    role = {
        "id": role_id,
        "name": name.strip(),
        "description": description.strip(),
        "permissions": [
            item for item in permissions if item in allowed_permissions
        ],
        "builtin": False,
    }
    data.setdefault("roles", _default_roles())[role_id] = role
    _save_auth_data(data)
    return role


def update_role(
    role_id: str,
    name: Optional[str] = None,
    permissions: Optional[list[str]] = None,
    description: Optional[str] = None,
) -> dict | None:
    data = _load_normalized_auth_data()
    roles = data.get("roles") or _default_roles()
    role = roles.get(role_id)
    if not role:
        return None
    if name is not None and name.strip():
        role["name"] = name.strip()
    if description is not None:
        role["description"] = description.strip()
    if permissions is not None:
        allowed_permissions = set(DEFAULT_PERMISSIONS)
        role["permissions"] = [
            item for item in permissions if item in allowed_permissions
        ]
    roles[role_id] = role
    data["roles"] = roles
    _save_auth_data(data)
    return {
        "id": role_id,
        "name": role.get("name", role_id),
        "description": role.get("description", ""),
        "permissions": list(role.get("permissions") or []),
        "builtin": bool(role.get("builtin", False)),
    }


def delete_role(role_id: str) -> bool:
    data = _load_normalized_auth_data()
    roles = data.get("roles") or _default_roles()
    role = roles.get(role_id)
    if not role or role.get("builtin"):
        return False
    for user in data.get("users", []):
        if role_id in (user.get("roles") or []):
            return False
    del roles[role_id]
    data["roles"] = roles
    _save_auth_data(data)
    return True


def list_users() -> list[dict]:
    data = _load_normalized_auth_data()
    return [_public_user(user) for user in data.get("users", [])]


def get_user(username: str) -> dict | None:
    data = _load_normalized_auth_data()
    _, user = _find_user(data, username)
    return _public_user(user) if user else None


# ---------------------------------------------------------------------------
# Token revocation (blacklist management)
# ---------------------------------------------------------------------------


def _is_token_revoked(jti: str) -> bool:
    """Check if a token ID (jti) is in the revocation list.

    Uses O(1) dict lookup via revoked_tokens_meta for performance.
    """
    data = _load_auth_data()
    meta = data.get("revoked_tokens_meta", {})
    return jti in meta


def _add_to_revocation_list(jti: str, exp: int) -> None:
    """Add a token ID to the revocation list with its expiry time.

    Uses revoked_tokens_meta dict for O(1) lookups. The revoked_tokens list
    is kept for backwards compatibility but not used for membership checks.
    """
    data = _load_auth_data()
    if data.get("_auth_load_error"):
        return

    # Initialize revoked_tokens_meta if not present
    if "revoked_tokens_meta" not in data:
        data["revoked_tokens_meta"] = {}

    # O(1) check using dict
    if jti not in data["revoked_tokens_meta"]:
        data["revoked_tokens_meta"][jti] = exp

        # Also add to list for backwards compatibility
        if "revoked_tokens" not in data:
            data["revoked_tokens"] = []
        data["revoked_tokens"].append(jti)

    _save_auth_data(data)


def _clean_expired_revocations() -> None:
    """
    Remove expired tokens from the revocation list to prevent unbounded growth.
    """
    data = _load_auth_data()
    if data.get("_auth_load_error"):
        return

    revoked = data.get("revoked_tokens", [])
    meta = data.get("revoked_tokens_meta", {})
    current_time = int(time.time())

    # Remove expired tokens
    cleaned_revoked = []
    cleaned_meta = {}

    for jti in revoked:
        exp = meta.get(jti, 0)
        if exp > current_time:
            cleaned_revoked.append(jti)
            cleaned_meta[jti] = exp

    if len(cleaned_revoked) < len(revoked):
        data["revoked_tokens"] = cleaned_revoked
        data["revoked_tokens_meta"] = cleaned_meta
        _save_auth_data(data)
        logger.info(
            "Cleaned %d expired tokens from revocation list",
            len(revoked) - len(cleaned_revoked),
        )


def is_auth_enabled() -> bool:
    """Check whether authentication is enabled via environment variable.

    Returns ``True`` when ``QWENPAW_AUTH_ENABLED`` is set to a truthy
    value (``true``, ``1``, ``yes``).  The presence of a registered
    user is checked separately by the middleware so that the first
    user can still reach the registration page.
    """
    env_flag = EnvVarLoader.get_str("QWENPAW_AUTH_ENABLED", "").strip().lower()
    return env_flag in ("true", "1", "yes")


def has_registered_users() -> bool:
    """Return ``True`` if a user has been registered."""
    data = _load_normalized_auth_data()
    return bool(data.get("users"))


# ---------------------------------------------------------------------------
# Registration (single-user)
# ---------------------------------------------------------------------------


def register_user(
    username: str,
    password: str,
    expiry_seconds: Optional[int] = None,
) -> Optional[str]:
    """Register the single user account.

    Args:
        username: The username to register.
        password: The password to register.
        expiry_seconds: Custom token expiry time in seconds.

    Returns a token on success, ``None`` if a user already exists.
    """
    data = _load_normalized_auth_data()

    # The first registered user becomes platform administrator.
    if data.get("users"):
        return None

    pw_hash, salt = _hash_password(password)
    ts = _now()
    data["users"] = [
        {
            "id": secrets.token_hex(8),
            "username": username,
            "password_hash": pw_hash,
            "password_salt": salt,
            "roles": ["admin"],
            "status": "active",
            "created_at": ts,
            "updated_at": ts,
        }
    ]

    # Ensure jwt_secret exists
    if not data.get("jwt_secret"):
        data["jwt_secret"] = secrets.token_hex(32)

    _save_auth_data(data)
    logger.info("User '%s' registered", username)
    return create_token(username, expiry_seconds)


def auto_register_from_env() -> None:
    """Auto-register admin user from environment variables.

    Called once during application startup.  If ``QWENPAW_AUTH_ENABLED``
    is truthy and both ``QWENPAW_AUTH_USERNAME`` and ``QWENPAW_AUTH_PASSWORD``
    are set, the admin account is created automatically — useful for
    Docker, Kubernetes, server-panel, and other automated deployments
    where interactive web registration is not practical.

    Skips silently when:
    - authentication is not enabled
    - a user has already been registered
    - either env var is missing or empty
    """
    if not is_auth_enabled():
        return
    if has_registered_users():
        return

    username = EnvVarLoader.get_str("QWENPAW_AUTH_USERNAME", "").strip()
    password = EnvVarLoader.get_str("QWENPAW_AUTH_PASSWORD", "").strip()
    if not username or not password:
        return

    token = register_user(username, password)
    if token:
        logger.info(
            "Auto-registered user '%s' from environment variables",
            username,
        )


def update_credentials(
    current_password: str,
    new_username: Optional[str] = None,
    new_password: Optional[str] = None,
    expiry_seconds: Optional[int] = None,
    username: Optional[str] = None,
) -> Optional[str]:
    """Update the registered user's username and/or password.

    Requires the current password for verification.  Returns a new
    token on success (because the username may have changed), or
    ``None`` if verification fails.

    Args:
        current_password: The current password for verification.
        new_username: The new username (optional).
        new_password: The new password (optional).
        expiry_seconds: Custom token expiry time in seconds.
    """
    data = _load_normalized_auth_data()
    user_idx = 0
    user = None
    if username:
        user_idx, user = _find_user(data, username)
    elif data.get("users"):
        user = data["users"][0]
    if not user:
        return None

    stored_hash = user.get("password_hash", "")
    stored_salt = user.get("password_salt", "")
    if not verify_password(current_password, stored_hash, stored_salt):
        return None

    if new_username and new_username.strip():
        user["username"] = new_username.strip()

    if new_password:
        pw_hash, salt = _hash_password(new_password)
        user["password_hash"] = pw_hash
        user["password_salt"] = salt
        # Rotate JWT secret to invalidate all existing sessions
        data["jwt_secret"] = secrets.token_hex(32)

    user["updated_at"] = _now()
    data["users"][user_idx] = user
    _save_auth_data(data)
    logger.info("Credentials updated for user '%s'", user["username"])
    return create_token(user["username"], expiry_seconds)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def authenticate(
    username: str,
    password: str,
    expiry_seconds: Optional[int] = None,
) -> Optional[str]:
    """Authenticate *username* / *password*.  Returns a token if valid.

    Args:
        username: The username to authenticate.
        password: The password to verify.
        expiry_seconds: Custom token expiry time in seconds.
    """
    data = _load_normalized_auth_data()
    _, user = _find_user(data, username)
    if not user:
        return None
    if user.get("status") != "active":
        return None
    if user.get("username") != username:
        return None
    stored_hash = user.get("password_hash", "")
    stored_salt = user.get("password_salt", "")
    if (
        stored_hash
        and stored_salt
        and verify_password(password, stored_hash, stored_salt)
    ):
        return create_token(username, expiry_seconds)
    return None


def revoke_token(token: str) -> bool:
    """Revoke a single token by adding its jti to the blacklist.

    Args:
        token: The token string to revoke.

    Returns True on success, False on failure.
    """
    import base64

    try:
        # Extract jti and exp from token
        parts = token.split(".", 1)
        if len(parts) != 2:
            return False

        payload_b64 = parts[0]
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        jti = payload.get("jti")
        exp = payload.get("exp", 0)

        if not jti:
            logger.warning("Token has no jti, cannot revoke individually")
            return False

        _add_to_revocation_list(jti, exp)
        logger.info("Token %s revoked", jti[:8])

        # Clean up expired tokens periodically
        _clean_expired_revocations()

        return True
    except Exception as exc:
        logger.error("Failed to revoke token: %s", exc)
        return False


def revoke_all_tokens() -> bool:
    """Revoke all existing tokens by rotating the JWT secret.

    This will invalidate all tokens that were issued before this call.
    Also clears the revocation list since all tokens are invalid anyway.
    Returns True on success, False on failure.
    """
    try:
        data = _load_auth_data()
        if data.get("_auth_load_error"):
            return False

        # Rotate JWT secret to invalidate all existing tokens
        data["jwt_secret"] = secrets.token_hex(32)

        # Clear revocation list since all tokens are now invalid
        data["revoked_tokens"] = []
        data["revoked_tokens_meta"] = {}

        _save_auth_data(data)
        logger.info("All tokens revoked (JWT secret rotated)")
        return True
    except Exception as exc:
        logger.error("Failed to revoke tokens: %s", exc)
        return False


def create_user(
    username: str,
    password: str,
    roles: Optional[list[str]] = None,
) -> dict | None:
    data = _load_normalized_auth_data()
    if data.get("_auth_load_error"):
        return None
    username = username.strip()
    if not username or not password.strip():
        return None
    if _find_user(data, username)[1] is not None:
        return None

    valid_roles = _valid_role_ids(data, roles or ["operator"]) or ["operator"]
    pw_hash, salt = _hash_password(password)
    ts = _now()
    user = {
        "id": secrets.token_hex(8),
        "username": username,
        "password_hash": pw_hash,
        "password_salt": salt,
        "roles": valid_roles,
        "status": "active",
        "created_at": ts,
        "updated_at": ts,
    }
    data.setdefault("users", []).append(user)
    _save_auth_data(data)
    logger.info("User '%s' created", username)
    return _public_user(user)


def update_user(
    username: str,
    roles: Optional[list[str]] = None,
    status: Optional[str] = None,
    password: Optional[str] = None,
) -> dict | None:
    data = _load_normalized_auth_data()
    idx, user = _find_user(data, username)
    if user is None:
        return None

    if roles is not None:
        valid_roles = _valid_role_ids(data, roles)
        user["roles"] = valid_roles or ["operator"]

    if status is not None:
        if status not in ("active", "disabled"):
            return None
        user["status"] = status

    if password is not None and password.strip():
        pw_hash, salt = _hash_password(password)
        user["password_hash"] = pw_hash
        user["password_salt"] = salt
        # Password reset invalidates all existing sessions.
        data["jwt_secret"] = secrets.token_hex(32)

    user["updated_at"] = _now()
    data["users"][idx] = user
    _save_auth_data(data)
    logger.info("User '%s' updated", username)
    return _public_user(user)


def delete_user(username: str) -> bool:
    data = _load_normalized_auth_data()
    users = data.get("users", [])
    idx, user = _find_user(data, username)
    if user is None:
        return False

    active_admins = [
        item
        for item in users
        if item.get("status") == "active"
        and "admin" in (item.get("roles") or [])
    ]
    if "admin" in (user.get("roles") or []) and len(active_admins) <= 1:
        return False

    del users[idx]
    data["users"] = users
    _save_auth_data(data)
    logger.info("User '%s' deleted", username)
    return True


# ---------------------------------------------------------------------------
# FastAPI middleware
# ---------------------------------------------------------------------------


def _resolve_client_ip(request: Request) -> str:
    """Return the real client IP, respecting reverse-proxy headers."""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else ""


def _agent_scoped_permission(path: str, method: str) -> str | None:
    """Return permission for /api/agents/{agentId}/... scoped APIs."""
    if not path.startswith("/api/agents/"):
        return None
    parts = path.split("/")
    if len(parts) < 5:
        if method in _MUTATING_METHODS:
            return "agents.manage"
        return "agents.use"

    scope = parts[4]
    if scope in {
        "agent-status",
        "chats",
        "console",
        "files",
        "messages",
    }:
        return "agents.use"
    if scope == "mcp":
        return "mcp.manage"
    if scope in {"skills", "tools"}:
        return "tools.manage"
    if scope in {"agent-stats", "token-usage"}:
        return "audit.view"
    if scope in {"backups", "config", "envs", "plugins", "settings"}:
        return "system.admin"
    if scope in {"cron", "plan", "workspace"}:
        return "agents.manage"
    return "agents.use"


def _required_permission(request: Request) -> str | None:
    from qwenpaw_ext.nexora.rbac import required_permission

    return required_permission(request.url.path, request.method)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that checks Bearer token on protected routes."""

    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        """Check Bearer token on protected API routes; skip public paths."""
        if self._should_skip_auth(request):
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return Response(
                content=json.dumps({"detail": "Not authenticated"}),
                status_code=401,
                media_type="application/json",
            )

        user = verify_token(token)
        if user is None:
            return Response(
                content=json.dumps(
                    {"detail": "Invalid or expired token"},
                ),
                status_code=401,
                media_type="application/json",
            )

        request.state.user = user
        request.state.roles = (get_user(user) or {}).get("roles", [])
        permission = _required_permission(request)
        if permission:
            from qwenpaw_ext.nexora.rbac import user_has_permission

            if not user_has_permission(user, permission):
                self._record_denied_audit(request, user, permission)
                return Response(
                    content=json.dumps(
                        {
                            "detail": "Permission denied",
                            "permission": permission,
                        },
                    ),
                    status_code=403,
                    media_type="application/json",
                )
        try:
            from qwenpaw_ext.nexora.governance import (
                enforce_agent_access_for_request,
            )

            enforce_agent_access_for_request(request)
        except Exception as exc:
            from fastapi import HTTPException

            if isinstance(exc, HTTPException):
                self._record_denied_audit(
                    request,
                    user,
                    permission,
                    detail={"reason": str(exc.detail)},
                )
                return Response(
                    content=json.dumps({"detail": exc.detail}),
                    status_code=exc.status_code,
                    media_type="application/json",
                )
            raise
        response = await call_next(request)
        self._record_request_audit(request, response, user, permission)
        return response

    @staticmethod
    def _should_skip_auth(request: Request) -> bool:
        """Return ``True`` when the request does not require auth."""
        if not is_auth_enabled() or not has_registered_users():
            return True

        path = request.url.path

        if request.method == "OPTIONS":
            return True

        if path in _PUBLIC_PATHS or any(
            path.startswith(p) for p in _PUBLIC_PREFIXES
        ):
            return True

        # Only protect /api/ routes
        if not path.startswith("/api/"):
            return True

        # A logged-in browser request should always pass through RBAC and
        # per-agent authorization, even when it comes from localhost.
        if AuthMiddleware._extract_token(request):
            return False

        # Check if client host is in allow_no_auth_hosts whitelist
        from ..config import load_config

        client_host = _resolve_client_ip(request)
        config = load_config()
        allowed_hosts = config.security.allow_no_auth_hosts
        return client_host in allowed_hosts

    @staticmethod
    def _extract_token(request: Request) -> Optional[str]:
        """Extract Bearer token from header or WebSocket query param."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        if "upgrade" in request.headers.get("connection", "").lower():
            return request.query_params.get("token")

        token = request.query_params.get("token")
        if token:
            return token
        return None

    @staticmethod
    def _record_request_audit(
        request: Request,
        response: Response,
        username: str,
        permission: str | None,
    ) -> None:
        path = request.url.path
        if request.method not in _MUTATING_METHODS:
            return
        if any(path.startswith(prefix) for prefix in _AUDIT_SKIP_PREFIXES):
            return

        try:
            from qwenpaw_ext.nexora.audit import record_audit_event

            query_str = str(request.url.query) if request.url.query else ""
            record_audit_event(
                actor=username,
                action="api.mutate",
                resource_type="api",
                resource_id=path,
                status="success" if response.status_code < 400 else "failure",
                detail={
                    "method": request.method,
                    "status_code": response.status_code,
                    "permission": permission or "",
                    **({"query": query_str} if query_str else {}),
                },
                request=request,
            )
        except Exception:
            logger.debug("Failed to record audit event", exc_info=True)

    @staticmethod
    def _record_denied_audit(
        request: Request,
        username: str,
        permission: str | None,
        detail: dict | None = None,
    ) -> None:
        try:
            from qwenpaw_ext.nexora.audit import record_audit_event

            record_audit_event(
                actor=username,
                action="api.denied",
                resource_type="api",
                resource_id=request.url.path,
                status="denied",
                detail={
                    "method": request.method,
                    "permission": permission or "",
                    **(detail or {}),
                },
                request=request,
            )
        except Exception:
            logger.debug("Failed to record denied audit event", exc_info=True)
