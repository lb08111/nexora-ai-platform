# -*- coding: utf-8 -*-
"""Authentication API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...constant import EnvVarLoader
from ..auth import (
    authenticate,
    get_user,
    has_registered_users,
    is_auth_enabled,
    register_user,
    revoke_all_tokens,
    revoke_token,
    update_credentials,
    verify_token,
)
from qwenpaw_ext.nexora.rbac import (
    create_role,
    create_user,
    delete_role,
    delete_user,
    list_permissions,
    list_roles,
    list_users,
    require_permission,
    update_role,
    update_user,
)
from qwenpaw_ext.nexora.audit import record_audit_event

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    expires_in: int | None = (
        None  # Token expiry in seconds, -1/0 for permanent
    )


class LoginResponse(BaseModel):
    token: str
    username: str
    roles: list[str] = []


class RegisterRequest(BaseModel):
    username: str
    password: str
    expires_in: int | None = (
        None  # Token expiry in seconds, -1/0 for permanent
    )


class AuthStatusResponse(BaseModel):
    enabled: bool
    has_users: bool


class UserInfo(BaseModel):
    id: str
    username: str
    roles: list[str]
    status: str
    created_at: int = 0
    updated_at: int = 0


class RoleInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    permissions: list[str]
    builtin: bool = False


class CurrentUserResponse(BaseModel):
    username: str
    roles: list[str]
    permissions: list[str]


class CreateUserRequest(BaseModel):
    username: str
    password: str
    roles: list[str] = ["operator"]


class UpdateUserRequest(BaseModel):
    roles: list[str] | None = None
    status: str | None = None
    password: str | None = None


class CreateRoleRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    permissions: list[str] = []


class UpdateRoleRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


def _current_username(request: Request) -> str:
    if not is_auth_enabled():
        return "__local_admin__"
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    username = verify_token(token) if token else None
    if username is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return username


def _require_user_admin(request: Request) -> str:
    username = _current_username(request)
    if username == "__local_admin__":
        return username
    require_permission(username, "users.manage")
    return username


def _require_user_view(request: Request) -> str:
    username = _current_username(request)
    if username == "__local_admin__":
        return username
    require_permission(username, "users.view")
    return username


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """Authenticate with username and password.

    Optional `expires_in` field:
    - Positive integer: token expires in N seconds
    - 0 or -1: permanent token (100 years)
    - None/omitted: default 7 days
    """
    if not is_auth_enabled():
        record_audit_event(
            actor="local-admin",
            action="auth.login",
            resource_type="auth",
            status="success",
            detail={"auth_enabled": False},
            request=request,
        )
        return LoginResponse(token="", username="")

    token = authenticate(req.username, req.password, req.expires_in)
    if token is None:
        record_audit_event(
            actor=req.username,
            action="auth.login",
            resource_type="auth",
            status="failure",
            detail={"reason": "invalid_credentials"},
            request=request,
        )
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    user = get_user(req.username)
    record_audit_event(
        actor=req.username,
        action="auth.login",
        resource_type="auth",
        status="success",
        detail={"roles": (user or {}).get("roles", [])},
        request=request,
    )
    return LoginResponse(
        token=token,
        username=req.username,
        roles=(user or {}).get("roles", []),
    )


@router.post("/register")
async def register(req: RegisterRequest, request: Request):
    """Register the single user account (only allowed once).

    Optional `expires_in` field:
    - Positive integer: token expires in N seconds
    - 0 or -1: permanent token (100 years)
    - None/omitted: default 7 days
    """
    env_flag = EnvVarLoader.get_str("QWENPAW_AUTH_ENABLED", "").strip().lower()
    if env_flag not in ("true", "1", "yes"):
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    if has_registered_users():
        raise HTTPException(
            status_code=403,
            detail="Usuário já cadastrado",
        )

    if not req.username.strip() or not req.password.strip():
        raise HTTPException(
            status_code=400,
            detail="Nome de usuário e senha são obrigatórios",
        )

    token = register_user(req.username.strip(), req.password, req.expires_in)
    if token is None:
        record_audit_event(
            actor=req.username.strip(),
            action="auth.register",
            resource_type="auth",
            status="failure",
            detail={"reason": "registration_failed"},
            request=request,
        )
        raise HTTPException(
            status_code=409,
            detail="Registration failed",
        )

    record_audit_event(
        actor=req.username.strip(),
        action="auth.register",
        resource_type="auth",
        status="success",
        detail={"roles": ["admin"]},
        request=request,
    )
    return LoginResponse(
        token=token, username=req.username.strip(), roles=["admin"]
    )


@router.get("/status")
async def auth_status():
    """Check if authentication is enabled and whether a user exists."""
    return AuthStatusResponse(
        enabled=is_auth_enabled(),
        has_users=has_registered_users(),
    )


@router.get("/verify")
async def verify(request: Request):
    """Verify that the caller's Bearer token is still valid."""
    if not is_auth_enabled():
        return {"valid": True, "username": ""}

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Nenhum token fornecido")

    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado",
        )

    user = get_user(username) or {}
    return {
        "valid": True,
        "username": username,
        "roles": user.get("roles", []),
    }


@router.get("/me", response_model=CurrentUserResponse)
async def me(request: Request):
    """Return current user roles and effective permissions."""
    username = _current_username(request)
    if username == "__local_admin__":
        return CurrentUserResponse(
            username="local-admin",
            roles=["admin"],
            permissions=list_permissions(),
        )
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    role_map = {role["id"]: role for role in list_roles()}
    permissions = set()
    for role_id in user["roles"]:
        role = role_map.get(role_id)
        if role:
            permissions.update(role["permissions"])
    return CurrentUserResponse(
        username=username,
        roles=user["roles"],
        permissions=sorted(permissions),
    )


@router.get("/users", response_model=list[UserInfo])
async def users(request: Request):
    """List platform users. Requires user-management permission."""
    _require_user_view(request)
    return list_users()


@router.post("/users", response_model=UserInfo)
async def add_user(req: CreateUserRequest, request: Request):
    """Create a platform user. Requires user-management permission."""
    _require_user_admin(request)
    user = create_user(req.username, req.password, req.roles)
    if user is None:
        raise HTTPException(status_code=400, detail="Falha ao criar usuário")
    return user


@router.put("/users/{username}", response_model=UserInfo)
async def modify_user(
    username: str,
    req: UpdateUserRequest,
    request: Request,
):
    """Update roles, status, or password for a platform user."""
    _require_user_admin(request)
    user = update_user(
        username=username,
        roles=req.roles,
        status=req.status,
        password=req.password,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.delete("/users/{username}")
async def remove_user(username: str, request: Request):
    """Delete a platform user."""
    current = _require_user_admin(request)
    if username == current:
        raise HTTPException(
            status_code=400, detail="Não é possível excluir a si mesmo"
        )
    if not delete_user(username):
        raise HTTPException(status_code=400, detail="Failed to delete user")
    return {"deleted": True}


@router.get("/roles", response_model=list[RoleInfo])
async def roles(request: Request):
    """List built-in roles and their permissions."""
    _require_user_view(request)
    return list_roles()


@router.post("/roles", response_model=RoleInfo)
async def add_role(req: CreateRoleRequest, request: Request):
    """Create a custom role."""
    _require_user_admin(request)
    role = create_role(
        role_id=req.id,
        name=req.name,
        description=req.description,
        permissions=req.permissions,
    )
    if role is None:
        raise HTTPException(status_code=400, detail="Falha ao criar papel")
    return role


@router.put("/roles/{role_id}", response_model=RoleInfo)
async def modify_role(
    role_id: str,
    req: UpdateRoleRequest,
    request: Request,
):
    """Update a role's display name, description, or permissions."""
    _require_user_admin(request)
    role = update_role(
        role_id=role_id,
        name=req.name,
        description=req.description,
        permissions=req.permissions,
    )
    if role is None:
        raise HTTPException(status_code=404, detail="Papel não encontrado")
    return role


@router.delete("/roles/{role_id}")
async def remove_role(role_id: str, request: Request):
    """Delete a custom role that is not assigned to any user."""
    _require_user_admin(request)
    if not delete_role(role_id):
        raise HTTPException(status_code=400, detail="Failed to delete role")
    return {"deleted": True}


@router.get("/permissions", response_model=list[str])
async def permissions(request: Request):
    """List platform permission points."""
    _require_user_view(request)
    return list_permissions()


class UpdateProfileRequest(BaseModel):
    current_password: str
    new_username: str | None = None
    new_password: str | None = None
    expires_in: int | None = (
        None  # Token expiry in seconds, -1/0 for permanent
    )


@router.post("/update-profile")
async def update_profile(req: UpdateProfileRequest, request: Request):
    """Update username and/or password for the authenticated user."""
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    if not has_registered_users():
        raise HTTPException(
            status_code=403,
            detail="No user registered",
        )

    # Verify caller is authenticated
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    caller_username = verify_token(caller_token) if caller_token else None
    if caller_username is None:
        raise HTTPException(status_code=401, detail="Não autenticado")

    if not req.new_username and not req.new_password:
        raise HTTPException(
            status_code=400,
            detail="Nada a atualizar",
        )

    if req.new_username is not None and not req.new_username.strip():
        raise HTTPException(
            status_code=400,
            detail="Username cannot be empty",
        )

    if req.new_password is not None and not req.new_password.strip():
        raise HTTPException(
            status_code=400,
            detail="Senha não pode estar vazia",
        )

    token = update_credentials(
        current_password=req.current_password,
        new_username=req.new_username,
        new_password=req.new_password,
        expiry_seconds=req.expires_in,
        username=caller_username,
    )
    if token is None:
        record_audit_event(
            actor=caller_username,
            action="auth.profile.update",
            resource_type="auth",
            status="failure",
            detail={"reason": "current_password_incorrect"},
            request=request,
        )
        raise HTTPException(
            status_code=401,
            detail="Senha atual está incorreta",
        )

    username = req.new_username.strip() if req.new_username else ""
    updated_username = username or caller_username
    user = get_user(updated_username) or {}
    record_audit_event(
        actor=caller_username,
        action="auth.profile.update",
        resource_type="auth",
        resource_id=updated_username,
        status="success",
        detail={
            "username_changed": bool(req.new_username),
            "password_changed": bool(req.new_password),
        },
        request=request,
    )
    return LoginResponse(
        token=token,
        username=updated_username,
        roles=user.get("roles", []),
    )


class RevokeTokenRequest(BaseModel):
    token: str | None = (
        None  # Optional: revoke specific token, or current if omitted
    )


@router.post("/revoke-token")
async def revoke_single_token(req: RevokeTokenRequest, request: Request):
    """Revoke a single token by adding it to the blacklist.

    If `token` is provided in the request body, revokes that token.
    If `token` is omitted, revokes the token used for authentication
    (current token).

    This allows you to:
    - Revoke a leaked token from another device
    - Logout from the current session
    """
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    # Get current token for authentication
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    caller_username = verify_token(caller_token) if caller_token else None
    if not caller_token or caller_username is None:
        raise HTTPException(status_code=401, detail="Não autenticado")

    # Determine which token to revoke
    token_to_revoke = req.token if req.token else caller_token
    is_current_token = token_to_revoke == caller_token

    success = revoke_token(token_to_revoke)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Falha ao revogar token",
        )

    record_audit_event(
        actor=caller_username,
        action="auth.logout",
        resource_type="auth",
        status="success",
        detail={"revoked_current_token": is_current_token},
        request=request,
    )
    message = (
        "Current token has been revoked. Please login again."
        if is_current_token
        else "Specified token has been revoked."
    )

    return {
        "message": message,
        "revoked": True,
        "revoked_current_token": is_current_token,
    }


@router.post("/revoke-all-tokens")
async def revoke_all_sessions(request: Request):
    """Revoke all existing tokens by rotating the JWT secret.

    This endpoint requires authentication. After calling this endpoint,
    all previously issued tokens will be invalidated, and you will need
    to login again to get a new token.

    This is more efficient than revoking tokens individually when you
    want to invalidate all sessions (e.g., password reset, security incident).
    """
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    # Verify caller is authenticated
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    caller_username = verify_token(caller_token) if caller_token else None
    if not caller_token or caller_username is None:
        raise HTTPException(status_code=401, detail="Não autenticado")

    success = revoke_all_tokens()
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Falha ao revogar tokens",
        )

    record_audit_event(
        actor=caller_username,
        action="auth.revoke_all_tokens",
        resource_type="auth",
        status="success",
        request=request,
    )
    return {
        "message": "Todos os tokens foram revogados. Por favor, faça login novamente.",
        "revoked": True,
    }
