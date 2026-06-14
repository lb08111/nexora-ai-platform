# -*- coding: utf-8 -*-
"""Jotaduo extension API routes."""
from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..auth import get_user, is_auth_enabled, verify_token
from ..utils import schedule_agent_reload
from ...config.config import (
    MCPClientConfig,
    MCPConfig,
    load_agent_config,
    save_agent_config,
)
from jotaduo_ext.jotaduo.approval_requests import (
    APPLIED,
    PENDING,
    REJECTED,
    create_approval_request,
    get_approval_request,
    list_approval_requests,
    update_approval_request,
)
from jotaduo_ext.jotaduo.audit import list_audit_events, record_audit_event
from jotaduo_ext.jotaduo.governance import (
    delete_policy,
    ensure_resource_policy,
    list_approval_policies,
    list_policies,
    role_ids_can_approve_action,
    upsert_approval_policy,
    upsert_policy,
)
from jotaduo_ext.jotaduo.rbac import require_permission

router = APIRouter(prefix="/jotaduo", tags=["jotaduo"])


VALID_ADD_POLICIES = {"none", "approval"}
VALID_REMOVE_POLICIES = {"none", "log", "approval"}


class GovernancePolicy(BaseModel):
    id: str | None = None
    source: str = Field(max_length=256)
    resource_id: str = Field(max_length=256)
    display_name: str = Field(default="", max_length=256)
    description: str = Field(default="", max_length=2000)
    risk_level: str = Field(default="low", max_length=32)
    allowed_agents: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    approval_required: bool = False
    audit_enabled: bool = True
    enabled: bool = True
    updated_at: int = 0


class ApprovalPolicy(BaseModel):
    id: str | None = None
    action: str = Field(max_length=256)
    display_name: str = Field(default="", max_length=256)
    description: str = Field(default="", max_length=2000)
    enabled: bool = True
    approver_roles: list[str] = Field(default_factory=list)
    allow_self_approval: bool = False
    updated_at: int = 0


class ApprovalRequest(BaseModel):
    id: str
    action: str = Field(max_length=256)
    status: str = PENDING
    requester: str = Field(default="", max_length=256)
    approver: str = Field(default="", max_length=256)
    resource_type: str = Field(default="", max_length=256)
    resource_id: str = Field(default="", max_length=256)
    resource_name: str = Field(default="", max_length=256)
    summary: str = Field(default="", max_length=2000)
    reason: str = Field(default="", max_length=2000)
    payload: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0


class ApprovalDecisionRequest(BaseModel):
    reason: str = ""


class AuditEvent(BaseModel):
    id: str
    timestamp: int
    actor: str
    action: str
    resource_type: str = ""
    resource_id: str = ""
    status: str = "success"
    ip: str = ""
    user_agent: str = ""
    detail: dict = Field(default_factory=dict)


class PageViewRequest(BaseModel):
    path: str
    title: str = ""


def _current_username(request: Request) -> str:
    if not is_auth_enabled():
        return "__local_admin__"
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    username = verify_token(token) if token else None
    if username is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


def _require_governance_view(request: Request) -> str:
    username = _current_username(request)
    if username != "__local_admin__":
        require_permission(username, "governance.view")
    return username


def _require_governance_manage(request: Request) -> str:
    username = _current_username(request)
    if username != "__local_admin__":
        require_permission(username, "governance.manage")
    return username


def _require_approval_manage(request: Request) -> str:
    username = _current_username(request)
    if username != "__local_admin__":
        require_permission(username, "approval.manage")
    return username


def _current_role_ids(username: str, request: Request) -> list[str]:
    if username == "__local_admin__":
        return ["admin"]
    roles = getattr(request.state, "roles", None)
    if isinstance(roles, list):
        return [str(role) for role in roles]
    user = get_user(username) or {}
    return [str(role) for role in user.get("roles") or []]


def _require_audit_view(request: Request) -> str:
    username = _current_username(request)
    if username != "__local_admin__":
        require_permission(username, "audit.view")
    return username


def _apply_mcp_create_approval(
    approval: dict,
    request: Request,
) -> dict:
    payload = approval.get("payload") or {}
    agent_id = str(payload.get("agent_id") or "")
    client_key = str(payload.get("client_key") or "")
    client_data = payload.get("client") or {}
    if not agent_id or not client_key or not isinstance(client_data, dict):
        raise HTTPException(
            status_code=400,
            detail="Invalid MCP approval payload",
        )

    agent_config = load_agent_config(agent_id)
    if agent_config.mcp is None:
        agent_config.mcp = MCPConfig(clients={})
    if client_key in agent_config.mcp.clients:
        raise HTTPException(
            status_code=409,
            detail=f"MCP client '{client_key}' already exists",
        )

    new_client = MCPClientConfig(**client_data)
    agent_config.mcp.clients[client_key] = new_client
    save_agent_config(agent_id, agent_config)
    policy = ensure_resource_policy(
        "mcp",
        client_key,
        display_name=new_client.name or client_key,
        description=new_client.description
        or new_client.url
        or new_client.command,
        allowed_agents=[agent_id],
    )
    schedule_agent_reload(request, agent_id)
    return {
        "agent_id": agent_id,
        "client_key": client_key,
        "resource_id": client_key,
        "governance_policy_id": policy["id"],
    }


def _apply_mcp_delete_approval(
    approval: dict,
    request: Request,
) -> dict:
    payload = approval.get("payload") or {}
    agent_id = str(payload.get("agent_id") or "")
    client_key = str(payload.get("client_key") or "")
    if not agent_id or not client_key:
        raise HTTPException(
            status_code=400,
            detail="Invalid MCP delete approval payload",
        )

    agent_config = load_agent_config(agent_id)
    if agent_config.mcp is None or client_key not in agent_config.mcp.clients:
        raise HTTPException(
            status_code=404,
            detail=f"MCP client '{client_key}' not found",
        )
    del agent_config.mcp.clients[client_key]
    save_agent_config(agent_id, agent_config)
    schedule_agent_reload(request, agent_id)
    return {
        "agent_id": agent_id,
        "client_key": client_key,
        "deleted": True,
    }


async def _apply_skill_create_approval(
    approval: dict,
    request: Request,
) -> dict:
    from jotaduo.agents.skill_system import SkillPoolService, SkillService
    from jotaduo.agents.skill_system.hub import (
        import_pool_skill_from_hub,
        install_skill_from_hub,
    )
    from jotaduo.app.routers.skills import (
        DownloadFromPoolRequest,
        PoolDownloadTarget,
        _execute_pool_download,
        _scan_error_payload,
        _workspace_dir_for_agent,
    )
    from jotaduo.constant import SECRET_DIR
    from jotaduo.security.skill_scanner import SkillScanError
    from agentscope_runtime.engine.schemas.exception import AppBaseException

    payload = approval.get("payload") or {}
    operation = str(payload.get("operation") or "")
    try:
        if operation == "workspace.create":
            agent_id = str(payload.get("agent_id") or "")
            skill = payload.get("skill") or {}
            if not agent_id or not isinstance(skill, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid workspace skill approval payload",
                )
            workspace_dir = _workspace_dir_for_agent(agent_id)
            created = SkillService(workspace_dir).create_skill(
                name=str(skill.get("name") or ""),
                content=str(skill.get("content") or ""),
                references=skill.get("references"),
                scripts=skill.get("scripts"),
                config=skill.get("config"),
                enable=bool(skill.get("enable", True)),
            )
            if not created:
                raise HTTPException(
                    status_code=409,
                    detail=f"Skill '{skill.get('name')}' already exists",
                )
            if skill.get("enable", True):
                schedule_agent_reload(request, agent_id)
            policy = ensure_resource_policy(
                "skill",
                str(created),
                display_name=str(created),
                allowed_agents=[agent_id],
            )
            return {
                "operation": operation,
                "agent_id": agent_id,
                "skill_name": created,
                "governance_policy_id": policy["id"],
            }

        if operation == "workspace.import_zip":
            agent_id = str(payload.get("agent_id") or "")
            staged_zip = Path(str(payload.get("staged_zip_path") or ""))
            if not agent_id:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid workspace skill zip approval payload",
                )
            upload_root = (
                SECRET_DIR / "jotaduo_approval_uploads" / "skills"
            ).resolve()
            staged_resolved = staged_zip.resolve()
            if not staged_resolved.is_relative_to(upload_root):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid staged skill path",
                )
            if not staged_resolved.is_file():
                raise HTTPException(
                    status_code=400,
                    detail="Staged skill upload is missing",
                )
            workspace_dir = _workspace_dir_for_agent(agent_id)
            data = staged_resolved.read_bytes()
            result = await asyncio.to_thread(
                SkillService(workspace_dir).import_from_zip,
                data=data,
                enable=bool(payload.get("enable", True)),
                target_name=str(payload.get("target_name") or ""),
                rename_map=payload.get("rename_map"),
            )
            if result.get("conflicts"):
                raise HTTPException(status_code=409, detail=result)
            if result.get("count", 0) > 0 and payload.get("enable", True):
                schedule_agent_reload(request, agent_id)
            staged_resolved.unlink(missing_ok=True)
            policy_ids = [
                ensure_resource_policy(
                    "skill",
                    str(skill_name),
                    display_name=str(skill_name),
                    allowed_agents=[agent_id],
                )["id"]
                for skill_name in result.get("imported", [])
            ]
            return {
                "operation": operation,
                "agent_id": agent_id,
                "imported": result.get("imported", []),
                "count": result.get("count", 0),
                "governance_policy_ids": policy_ids,
            }

        if operation == "workspace.download_from_pool":
            skill_name = str(payload.get("skill_name") or "")
            raw_targets = payload.get("targets") or []
            targets = [
                PoolDownloadTarget(
                    workspace_id=str(target.get("workspace_id") or ""),
                )
                for target in raw_targets
                if isinstance(target, dict)
            ]
            if not skill_name or not targets:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid pool broadcast approval payload",
                )
            result = _execute_pool_download(
                DownloadFromPoolRequest(
                    skill_name=skill_name,
                    targets=targets,
                    all_workspaces=False,
                    overwrite=bool(payload.get("overwrite", False)),
                    preview_only=False,
                ),
            )
            target_ids = [
                str(item.get("workspace_id") or "")
                for item in result.get("downloaded", [])
                if item.get("workspace_id")
            ]
            policy = ensure_resource_policy(
                "skill",
                skill_name,
                display_name=skill_name,
                allowed_agents=target_ids,
            )
            return {
                "operation": operation,
                "skill_name": skill_name,
                "downloaded": result.get("downloaded", []),
                "governance_policy_id": policy["id"],
            }

        if operation == "workspace.hub_install":
            agent_id = str(payload.get("agent_id") or "")
            hub = payload.get("hub") or {}
            if not agent_id or not isinstance(hub, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid hub install approval payload",
                )
            workspace_dir = _workspace_dir_for_agent(agent_id)
            result = await install_skill_from_hub(
                workspace_dir=workspace_dir,
                bundle_url=str(hub.get("bundle_url") or ""),
                version=str(hub.get("version") or ""),
                enable=bool(hub.get("enable", True)),
                target_name=str(hub.get("target_name") or ""),
            )
            if result.enabled:
                schedule_agent_reload(request, agent_id)
            policy = ensure_resource_policy(
                "skill",
                result.name,
                display_name=result.name,
                description=result.source_url,
                allowed_agents=[agent_id],
            )
            return {
                "operation": operation,
                "agent_id": agent_id,
                "skill_name": result.name,
                "enabled": result.enabled,
                "source_url": result.source_url,
                "installed_from": result.installed_from,
                "governance_policy_id": policy["id"],
            }

        if operation == "pool.create":
            skill = payload.get("skill") or {}
            if not isinstance(skill, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid pool skill approval payload",
                )
            created = SkillPoolService().create_skill(
                name=str(skill.get("name") or ""),
                content=str(skill.get("content") or ""),
                references=skill.get("references"),
                scripts=skill.get("scripts"),
                config=skill.get("config"),
            )
            if not created:
                raise HTTPException(
                    status_code=409,
                    detail=f"Skill '{skill.get('name')}' already exists",
                )
            policy = ensure_resource_policy(
                "skill",
                str(created),
                display_name=str(created),
                allowed_agents=[],
            )
            return {
                "operation": operation,
                "skill_name": created,
                "governance_policy_id": policy["id"],
            }

        if operation == "pool.import_zip":
            staged_zip = Path(str(payload.get("staged_zip_path") or ""))
            upload_root = (
                SECRET_DIR / "jotaduo_approval_uploads" / "skills"
            ).resolve()
            staged_resolved = staged_zip.resolve()
            if not staged_resolved.is_relative_to(upload_root):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid staged skill path",
                )
            if not staged_resolved.is_file():
                raise HTTPException(
                    status_code=400,
                    detail="Staged skill upload is missing",
                )
            data = staged_resolved.read_bytes()
            result = await asyncio.to_thread(
                SkillPoolService().import_from_zip,
                data=data,
                target_name=str(payload.get("target_name") or ""),
                rename_map=payload.get("rename_map"),
            )
            if result.get("conflicts"):
                raise HTTPException(status_code=409, detail=result)
            staged_resolved.unlink(missing_ok=True)
            policy_ids = [
                ensure_resource_policy(
                    "skill",
                    str(skill_name),
                    display_name=str(skill_name),
                    allowed_agents=[],
                )["id"]
                for skill_name in result.get("imported", [])
            ]
            return {
                "operation": operation,
                "imported": result.get("imported", []),
                "count": result.get("count", 0),
                "governance_policy_ids": policy_ids,
            }

        if operation == "pool.import_hub":
            hub = payload.get("hub") or {}
            if not isinstance(hub, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid hub skill approval payload",
                )
            result = await import_pool_skill_from_hub(
                bundle_url=str(hub.get("bundle_url") or ""),
                version=str(hub.get("version") or ""),
                target_name=str(hub.get("target_name") or ""),
            )
            return {
                "operation": operation,
                "skill_name": result.name,
                "source_url": result.source_url,
                "installed_from": result.installed_from,
                "governance_policy_id": ensure_resource_policy(
                    "skill",
                    result.name,
                    display_name=result.name,
                    description=result.source_url,
                    allowed_agents=[],
                )["id"],
            }
    except SkillScanError as exc:
        raise HTTPException(
            status_code=422,
            detail=_scan_error_payload(exc),
        ) from exc
    except (ValueError, AppBaseException) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Skill approval execution failed: {exc}",
        ) from exc

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported skill approval operation '{operation}'",
    )


async def _load_plugin_from_source_path(
    request: Request,
    source_path: Path,
    force: bool,
) -> dict:
    from jotaduo.app.routers.plugins import (
        _collect_plugin_runtime_ids,
        _post_load_setup,
        _post_unload_cleanup,
    )
    from jotaduo.config.utils import get_plugins_dir

    loader = getattr(request.app.state, "plugin_loader", None)
    if loader is None:
        raise HTTPException(
            status_code=503,
            detail="Plugin loader is not ready yet. Try again shortly.",
        )

    if force:
        manifest_path = source_path / "plugin.json"
        if manifest_path.exists():
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid plugin manifest: {exc}",
                ) from exc
            existing_id = raw.get("id")
            if (
                existing_id
                and loader.get_loaded_plugin(existing_id) is not None
            ):
                pids, cmds = _collect_plugin_runtime_ids(
                    loader.registry,
                    existing_id,
                )
                await loader.unload_plugin(existing_id, delete_files=False)
                _post_unload_cleanup(request, existing_id, pids, cmds)

    try:
        record = await loader.load_plugin_from_path(
            source_path=source_path,
            install_dir=get_plugins_dir(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Plugin installation failed: {exc}",
        ) from exc

    await _post_load_setup(request, record.manifest.id)
    policy = ensure_resource_policy(
        "plugin",
        record.manifest.id,
        display_name=record.manifest.name or record.manifest.id,
        description=record.manifest.description,
        allowed_agents=[],
        risk_level="high",
    )
    return {
        "id": record.manifest.id,
        "name": record.manifest.name,
        "version": record.manifest.version,
        "description": record.manifest.description,
        "author": record.manifest.author,
        "loaded": True,
        "governance_policy_id": policy["id"],
    }


async def _apply_skill_delete_approval(
    approval: dict,
    request: Request,
) -> dict:
    from jotaduo.agents.skill_system import SkillPoolService, SkillService
    from jotaduo.app.routers.skills import _workspace_dir_for_agent

    payload = approval.get("payload") or {}
    operation = str(payload.get("operation") or "")

    if operation == "workspace.delete":
        agent_id = str(payload.get("agent_id") or "")
        skill_name = str(payload.get("skill_name") or "")
        if not agent_id or not skill_name:
            raise HTTPException(
                status_code=400,
                detail="Invalid skill delete payload",
            )
        workspace_dir = _workspace_dir_for_agent(agent_id)
        service = SkillService(workspace_dir)
        service.disable_skill(skill_name)
        deleted = service.delete_skill(skill_name)
        if not deleted:
            raise HTTPException(
                status_code=409,
                detail="Skill could not be deleted",
            )
        return {
            "operation": operation,
            "agent_id": agent_id,
            "skill_name": skill_name,
            "deleted": True,
        }

    if operation == "workspace.batch_delete":
        agent_id = str(payload.get("agent_id") or "")
        skill_names = payload.get("skill_names") or []
        if not agent_id or not skill_names:
            raise HTTPException(
                status_code=400,
                detail="Invalid batch skill delete payload",
            )
        workspace_dir = _workspace_dir_for_agent(agent_id)
        service = SkillService(workspace_dir)
        results = {}
        for name in skill_names:
            try:
                service.disable_skill(name)
                results[name] = service.delete_skill(name)
            except Exception:
                results[name] = False
        return {
            "operation": operation,
            "agent_id": agent_id,
            "results": results,
        }

    if operation == "pool.delete":
        skill_name = str(payload.get("skill_name") or "")
        if not skill_name:
            raise HTTPException(
                status_code=400,
                detail="Invalid pool skill delete payload",
            )
        deleted = SkillPoolService().delete_skill(skill_name)
        if not deleted:
            raise HTTPException(
                status_code=409,
                detail="Pool skill could not be deleted",
            )
        return {
            "operation": operation,
            "skill_name": skill_name,
            "deleted": True,
        }

    if operation == "pool.batch_delete":
        skill_names = payload.get("skill_names") or []
        if not skill_names:
            raise HTTPException(
                status_code=400,
                detail="Invalid batch pool skill delete payload",
            )
        service = SkillPoolService()
        results = {}
        for name in skill_names:
            try:
                results[name] = service.delete_skill(name)
            except Exception:
                results[name] = False
        return {"operation": operation, "results": results}

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported skill delete operation '{operation}'",
    )


async def _apply_plugin_install_approval(
    approval: dict,
    request: Request,
) -> dict:
    from jotaduo.app.routers.plugins import _find_plugin_dir, _safe_extract_zip
    from jotaduo.constant import SECRET_DIR

    payload = approval.get("payload") or {}
    operation = str(payload.get("operation") or "")
    force = bool(payload.get("force", False))
    temp_dir: Path | None = None
    try:
        if operation == "install_source":
            source = str(payload.get("source") or "").strip()
            if not source:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid plugin approval payload",
                )
            if source.startswith(("http://", "https://")):
                from jotaduo.app.routers.plugins import _async_download

                temp_dir = Path(tempfile.mkdtemp())
                zip_path = temp_dir / "plugin.zip"
                await _async_download(source, zip_path)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    _safe_extract_zip(zf, temp_dir)
                zip_path.unlink(missing_ok=True)
                source_path = _find_plugin_dir(temp_dir)
            else:
                source_path = Path(source).resolve()
                if not source_path.exists():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Path not found: {source}",
                    )
            result = await _load_plugin_from_source_path(
                request,
                source_path,
                force,
            )
            result["operation"] = operation
            return result

        if operation == "install_uploaded_zip":
            staged_zip = Path(str(payload.get("staged_zip_path") or ""))
            upload_root = (
                SECRET_DIR / "jotaduo_approval_uploads" / "plugins"
            ).resolve()
            staged_resolved = staged_zip.resolve()
            if not staged_resolved.is_relative_to(upload_root):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid staged plugin path",
                )
            if not staged_resolved.is_file():
                raise HTTPException(
                    status_code=400,
                    detail="Staged plugin upload is missing",
                )
            temp_dir = Path(tempfile.mkdtemp())
            with zipfile.ZipFile(staged_resolved, "r") as zf:
                _safe_extract_zip(zf, temp_dir)
            source_path = _find_plugin_dir(temp_dir)
            result = await _load_plugin_from_source_path(
                request,
                source_path,
                force,
            )
            result["operation"] = operation
            staged_resolved.unlink(missing_ok=True)
            return result
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported plugin approval operation '{operation}'",
    )


async def _apply_plugin_uninstall_approval(
    approval: dict,
    request: Request,
) -> dict:
    payload = approval.get("payload") or {}
    plugin_id = str(payload.get("plugin_id") or "")
    if not plugin_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid plugin uninstall payload",
        )

    loader = getattr(request.app.state, "plugin_loader", None)
    if loader is None:
        raise HTTPException(
            status_code=503,
            detail="Plugin loader is not ready",
        )

    record = loader.get_loaded_plugin(plugin_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{plugin_id}' is not loaded",
        )

    from .plugins import (
        _collect_plugin_runtime_ids,
        _post_unload_cleanup,
        _remove_plugin_tools_from_agents,
        _schedule_all_agents_reload,
    )

    meta: dict = record.manifest.meta or {}
    provider_ids, command_names = _collect_plugin_runtime_ids(
        loader.registry,
        plugin_id,
    )
    await loader.unload_plugin(plugin_id, delete_files=True)
    _post_unload_cleanup(request, plugin_id, provider_ids, command_names)
    _remove_plugin_tools_from_agents(plugin_id, meta)
    _schedule_all_agents_reload(request)
    return {"plugin_id": plugin_id, "deleted": True}


async def _apply_approval_request(approval: dict, request: Request) -> dict:
    if approval["action"] == "mcp.create":
        return _apply_mcp_create_approval(approval, request)
    if approval["action"] == "mcp.delete":
        return _apply_mcp_delete_approval(approval, request)
    if approval["action"] == "skill.create":
        return await _apply_skill_create_approval(approval, request)
    if approval["action"] == "skill.delete":
        return await _apply_skill_delete_approval(approval, request)
    if approval["action"] == "plugin.install":
        return await _apply_plugin_install_approval(approval, request)
    if approval["action"] == "plugin.uninstall":
        return await _apply_plugin_uninstall_approval(approval, request)
    raise HTTPException(
        status_code=400,
        detail=f"Approval action '{approval['action']}' is not supported yet",
    )


@router.get("/governance/policies", response_model=list[GovernancePolicy])
async def governance_policies(request: Request):
    """List AIops governance policies for native JotaDuo resources."""
    _require_governance_view(request)
    return list_policies()


@router.post("/governance/policies", response_model=GovernancePolicy)
async def save_governance_policy(req: GovernancePolicy, request: Request):
    """Create or update a governance policy."""
    _require_governance_manage(request)
    if not req.source.strip() or not req.resource_id.strip():
        raise HTTPException(
            status_code=400,
            detail="source and resource_id are required",
        )
    return upsert_policy(req.dict())


@router.delete("/governance/policies/{policy_id}")
async def remove_governance_policy(policy_id: str, request: Request):
    """Remove an override policy. The resource itself is not deleted."""
    _require_governance_manage(request)
    if not delete_policy(policy_id):
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"deleted": True}


@router.get(
    "/governance/approval-policies",
    response_model=list[ApprovalPolicy],
)
async def approval_policies(request: Request):
    """List approval policies for creating new platform capabilities."""
    _require_governance_view(request)
    return list_approval_policies()


@router.post(
    "/governance/approval-policies",
    response_model=ApprovalPolicy,
)
async def save_approval_policy(req: ApprovalPolicy, request: Request):
    """Create or update an approval policy."""
    _require_governance_manage(request)
    if not req.action.strip():
        raise HTTPException(status_code=400, detail="action is required")
    try:
        return upsert_approval_policy(req.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/approval-requests",
    response_model=list[ApprovalRequest],
)
async def approval_requests(
    request: Request,
    status: str | None = Query(default=None),
    action: str | None = Query(default=None),
):
    """List platform capability approval requests."""
    _require_approval_manage(request)
    return list_approval_requests(status=status, action=action)


@router.post(
    "/approval-requests/{request_id}/approve",
    response_model=ApprovalRequest,
)
async def approve_platform_approval_request(
    request_id: str,
    req: ApprovalDecisionRequest,
    request: Request,
):
    """Approve and apply a pending platform capability request."""
    username = _require_approval_manage(request)
    approval = get_approval_request(request_id)
    if approval is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found",
        )
    if approval["status"] != PENDING:
        raise HTTPException(
            status_code=409,
            detail="Approval request is not pending",
        )

    role_ids = _current_role_ids(username, request)
    if not role_ids_can_approve_action(
        role_ids,
        approval["action"],
        actor=username,
        requester=approval["requester"],
    ):
        raise HTTPException(status_code=403, detail="Approval not allowed")

    try:
        result = await _apply_approval_request(approval, request)
    except HTTPException as exc:
        update_approval_request(
            request_id,
            {
                "status": "failed",
                "approver": username,
                "reason": req.reason,
                "result": {"detail": exc.detail},
            },
        )
        raise

    updated = update_approval_request(
        request_id,
        {
            "status": APPLIED,
            "approver": username,
            "reason": req.reason,
            "result": result,
        },
    )
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found",
        )
    record_audit_event(
        actor=username,
        action=f"{approval['action']}.approved",
        resource_type=approval["resource_type"],
        resource_id=approval["resource_id"],
        detail={"approval_request_id": request_id, "result": result},
        request=request,
    )
    return updated


@router.post(
    "/approval-requests/{request_id}/reject",
    response_model=ApprovalRequest,
)
async def reject_platform_approval_request(
    request_id: str,
    req: ApprovalDecisionRequest,
    request: Request,
):
    """Reject a pending platform capability request."""
    username = _require_approval_manage(request)
    approval = get_approval_request(request_id)
    if approval is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found",
        )
    if approval["status"] != PENDING:
        raise HTTPException(
            status_code=409,
            detail="Approval request is not pending",
        )

    is_own_request = username == approval["requester"]
    role_ids = _current_role_ids(username, request)
    if not is_own_request and not role_ids_can_approve_action(
        role_ids,
        approval["action"],
        actor=username,
        requester="",
    ):
        raise HTTPException(status_code=403, detail="Approval not allowed")

    updated = update_approval_request(
        request_id,
        {
            "status": REJECTED,
            "approver": username,
            "reason": req.reason,
        },
    )
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found",
        )
    record_audit_event(
        actor=username,
        action=f"{approval['action']}.rejected",
        resource_type=approval["resource_type"],
        resource_id=approval["resource_id"],
        detail={"approval_request_id": request_id, "reason": req.reason},
        request=request,
    )
    return updated


@router.get("/audit/events", response_model=list[AuditEvent])
async def audit_events(
    request: Request,
    limit: int = Query(default=200, ge=1, le=1000),
    actor: str | None = None,
    action: str | None = None,
    status: str | None = None,
    start_time: int | None = Query(default=None),
    end_time: int | None = Query(default=None),
):
    """List recent platform audit events."""
    _require_audit_view(request)
    return list_audit_events(
        limit=limit,
        actor=actor,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/audit/events/export")
async def audit_events_export(
    request: Request,
    limit: int = Query(default=5000, ge=1, le=50000),
    actor: str | None = None,
    action: str | None = None,
    status: str | None = None,
    start_time: int | None = Query(default=None),
    end_time: int | None = Query(default=None),
):
    """Export audit events as CSV."""
    import csv
    import io
    from datetime import datetime, timezone

    _require_audit_view(request)
    events = list_audit_events(
        limit=limit,
        actor=actor,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )

    buf = io.StringIO()
    # BOM for Excel to recognize UTF-8
    buf.write("﻿")
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Horário",
            "Usuário",
            "Operação",
            "Resultado",
            "Tipo de Recurso",
            "ID do Recurso",
            "IP de Origem",
            "Detalhes",
        ],
    )
    for e in events:
        ts = e.get("timestamp", 0)
        time_str = (
            datetime.fromtimestamp(ts, tz=timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
            if ts
            else ""
        )
        detail = e.get("detail")
        detail_str = json.dumps(detail, ensure_ascii=False) if detail else ""
        writer.writerow(
            [
                time_str,
                e.get("actor", ""),
                e.get("action", ""),
                e.get("status", ""),
                e.get("resource_type", ""),
                e.get("resource_id", ""),
                e.get("ip", ""),
                detail_str,
            ],
        )

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="audit_logs_{now_str}.csv"',
        },
    )


@router.post("/audit/page-view")
async def audit_page_view(req: PageViewRequest, request: Request):
    """Record a user page view in the platform console."""
    username = _current_username(request)
    record_audit_event(
        actor=username,
        action="page.view",
        resource_type="page",
        resource_id=req.path,
        detail={"title": req.title},
        request=request,
    )
    return {"recorded": True}


# ═══════════════════════════════════════════════════════════════════════════
# Token usage per user
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/token-usage/by-user")
async def token_usage_by_user(
    request: Request,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    """按用户统计 Token 消耗。"""
    _require_audit_view(request)
    from jotaduo_ext.jotaduo.db import is_database_enabled, get_engine

    if not is_database_enabled():
        return []
    from sqlalchemy import text
    from datetime import date as date_type, timedelta

    end_d = (
        date_type.fromisoformat(end_date) if end_date else date_type.today()
    )
    start_d = (
        date_type.fromisoformat(start_date)
        if start_date
        else end_d - timedelta(days=30)
    )
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT actor, agent_id, provider_id, model, "
                "SUM(prompt_tokens) AS prompt_tokens, "
                "SUM(completion_tokens) AS completion_tokens, "
                "SUM(call_count) AS call_count "
                "FROM jotaduo_token_usage "
                "WHERE date >= :s AND date <= :e "
                "GROUP BY actor, agent_id, provider_id, model "
                "ORDER BY SUM(prompt_tokens + completion_tokens) DESC",
            ),
            {"s": start_d, "e": end_d},
        ).fetchall()
    return [
        {
            "actor": r[0],
            "agent_id": r[1],
            "provider_id": r[2],
            "model": r[3],
            "prompt_tokens": int(r[4]),
            "completion_tokens": int(r[5]),
            "call_count": int(r[6]),
        }
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Multi-tenant: Agent grants, templates, capability approval config
# ═══════════════════════════════════════════════════════════════════════════


class AgentGrantRequest(BaseModel):
    usernames: list[str]


class AgentGrantResponse(BaseModel):
    agent_id: str
    username: str
    granted_by: str = ""
    granted_at: int = 0


class CapabilityApprovalConfigModel(BaseModel):
    capability_type: str
    add_policy: str = "approval"
    remove_policy: str = "log"
    approver_roles: list[str] = Field(default_factory=lambda: ["admin"])
    updated_at: int = 0


class CapabilityApprovalConfigUpdateModel(BaseModel):
    add_policy: str | None = Field(default=None, max_length=32)
    remove_policy: str | None = Field(default=None, max_length=32)
    approver_roles: list[str] | None = None


class AgentTemplateModel(BaseModel):
    template_id: str | None = None
    name: str = Field(max_length=256)
    description: str = Field(default="", max_length=2000)
    capabilities: dict = Field(default_factory=dict)


class AgentTemplateUpdateModel(BaseModel):
    name: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=2000)
    capabilities: dict | None = None


# --- Agent grants ---


@router.get(
    "/agent-grants/{agent_id}",
    response_model=list[AgentGrantResponse],
    summary="List users granted to an agent",
)
async def list_agent_grants(agent_id: str, request: Request):
    _require_governance_view(request)
    from jotaduo_ext.jotaduo import agent_grants

    return agent_grants.list_grants_for_agent(agent_id)


@router.get(
    "/agent-grants/user/{username}",
    response_model=list[AgentGrantResponse],
    summary="List agents granted to a user",
)
async def list_user_grants(username: str, request: Request):
    _require_governance_view(request)
    from jotaduo_ext.jotaduo import agent_grants

    return agent_grants.list_grants_for_user(username)


@router.post(
    "/agent-grants/{agent_id}",
    summary="Grant agent to users (batch)",
)
async def grant_agent_to_users(
    agent_id: str,
    req: AgentGrantRequest,
    request: Request,
):
    admin_user = _require_governance_manage(request)
    if not req.usernames:
        raise HTTPException(status_code=400, detail="usernames is required")
    from jotaduo_ext.jotaduo import agent_grants

    count = agent_grants.batch_grant_agent(agent_id, req.usernames, admin_user)
    record_audit_event(
        actor=admin_user,
        action="agent.grant",
        resource_type="agent",
        resource_id=agent_id,
        detail={"usernames": req.usernames, "count": count},
        request=request,
    )
    return {"agent_id": agent_id, "granted_count": count}


@router.delete(
    "/agent-grants/{agent_id}",
    summary="Revoke agent from users (batch)",
)
async def revoke_agent_from_users(
    agent_id: str,
    req: AgentGrantRequest,
    request: Request,
):
    admin_user = _require_governance_manage(request)
    if not req.usernames:
        raise HTTPException(status_code=400, detail="usernames is required")
    from jotaduo_ext.jotaduo import agent_grants

    count = agent_grants.batch_revoke_agent(agent_id, req.usernames)
    record_audit_event(
        actor=admin_user,
        action="agent.revoke",
        resource_type="agent",
        resource_id=agent_id,
        detail={"usernames": req.usernames, "count": count},
        request=request,
    )
    return {"agent_id": agent_id, "revoked_count": count}


# --- Capability approval config ---


@router.get(
    "/capability-approval-config",
    response_model=list[CapabilityApprovalConfigModel],
    summary="List per-capability-type approval configuration",
)
async def list_capability_approval_configs(request: Request):
    _require_governance_view(request)
    from jotaduo_ext.jotaduo import capability_approval

    configs = capability_approval.list_configs()
    if not configs:
        capability_approval.ensure_default_configs()
        configs = capability_approval.list_configs()
    return configs


@router.put(
    "/capability-approval-config/{capability_type}",
    response_model=CapabilityApprovalConfigModel,
    summary="Update approval configuration for a capability type",
)
async def update_capability_approval_config(
    capability_type: str,
    req: CapabilityApprovalConfigUpdateModel,
    request: Request,
):
    admin_user = _require_governance_manage(request)
    from jotaduo_ext.jotaduo import capability_approval

    if capability_type not in capability_approval.CAPABILITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability type: {capability_type}",
        )
    if req.add_policy is not None and req.add_policy not in VALID_ADD_POLICIES:
        raise HTTPException(
            status_code=400,
            detail=f"add_policy must be one of {sorted(VALID_ADD_POLICIES)}",
        )
    if (
        req.remove_policy is not None
        and req.remove_policy not in VALID_REMOVE_POLICIES
    ):
        raise HTTPException(
            status_code=400,
            detail=f"remove_policy must be one of {sorted(VALID_REMOVE_POLICIES)}",
        )
    updates = {
        k: v
        for k, v in {
            "add_policy": req.add_policy,
            "remove_policy": req.remove_policy,
            "approver_roles": req.approver_roles,
        }.items()
        if v is not None
    }
    result = capability_approval.partial_update_config(
        capability_type,
        updates,
    )
    record_audit_event(
        actor=admin_user,
        action="capability_approval.update",
        resource_type="capability_approval_config",
        resource_id=capability_type,
        detail={k: v for k, v in updates.items() if k != "capability_type"},
        request=request,
    )
    return result


# --- Agent templates ---


@router.get(
    "/agent-templates",
    response_model=list[AgentTemplateModel],
    summary="List agent initialization templates",
)
async def list_agent_templates(request: Request):
    _require_governance_view(request)
    from jotaduo_ext.jotaduo import agent_templates

    templates = agent_templates.list_templates()
    if not templates:
        agent_templates.ensure_builtin_templates()
        templates = agent_templates.list_templates()
    return templates


@router.get(
    "/agent-templates/{template_id}",
    response_model=AgentTemplateModel,
    summary="Get a specific template",
)
async def get_agent_template(template_id: str, request: Request):
    _require_governance_view(request)
    from jotaduo_ext.jotaduo import agent_templates

    t = agent_templates.get_template(template_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@router.post(
    "/agent-templates",
    response_model=AgentTemplateModel,
    summary="Create a new agent template",
)
async def create_agent_template(
    req: AgentTemplateModel,
    request: Request,
):
    admin_user = _require_governance_manage(request)
    from jotaduo_ext.jotaduo import agent_templates

    t = agent_templates.create_template(
        {
            "template_id": req.template_id,
            "name": req.name,
            "description": req.description,
            "capabilities": req.capabilities,
            "created_by": admin_user,
        },
    )
    record_audit_event(
        actor=admin_user,
        action="agent_template.create",
        resource_type="agent_template",
        resource_id=t["template_id"],
        detail={"name": req.name},
        request=request,
    )
    return t


@router.put(
    "/agent-templates/{template_id}",
    response_model=AgentTemplateModel,
    summary="Update an existing template",
)
async def update_agent_template(
    template_id: str,
    req: AgentTemplateUpdateModel,
    request: Request,
):
    admin_user = _require_governance_manage(request)
    from jotaduo_ext.jotaduo import agent_templates

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.capabilities is not None:
        updates["capabilities"] = req.capabilities
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    t = agent_templates.update_template(template_id, updates)
    if t is None:
        raise HTTPException(status_code=404, detail="Template not found")
    record_audit_event(
        actor=admin_user,
        action="agent_template.update",
        resource_type="agent_template",
        resource_id=template_id,
        detail=updates,
        request=request,
    )
    return t


@router.delete("/agent-templates/{template_id}")
async def delete_agent_template(template_id: str, request: Request):
    admin_user = _require_governance_manage(request)
    from jotaduo_ext.jotaduo import agent_templates

    if not agent_templates.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    record_audit_event(
        actor=admin_user,
        action="agent_template.delete",
        resource_type="agent_template",
        resource_id=template_id,
        request=request,
    )
    return {"deleted": True}
