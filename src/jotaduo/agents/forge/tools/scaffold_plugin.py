# -*- coding: utf-8 -*-
"""Scaffold a JotaDuo plugin bundle (manifest + entry class + router)."""

from __future__ import annotations

import json

from jotaduo.agents.br_team.tools._utils import json_response, text_response

from .._paths import kebab, slugify, write_files

__all__ = ["scaffold_plugin"]


_PLUGIN_PY = '''\
# -*- coding: utf-8 -*-
"""{title} plugin for JotaDuo — gerado pelo AgentForge."""

from __future__ import annotations

import logging

logger = logging.getLogger("jotaduo").getChild("plugin.{plugin_id}")


class {class_name}:
    """{title} plugin entry point."""

    def register(self, api):
        logger.info("{class_name}.register() called")
        try:
            from .routers_setup import build_plugin_routers

            for router, prefix in build_plugin_routers():
                api.register_http_router(router, prefix=prefix)
                logger.info(
                    "[{plugin_id}] registered router at /api%s",
                    prefix,
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "[{plugin_id}] failed to register routers: %s",
                exc,
            )

        api.register_startup_hook(
            hook_name="{plugin_id_us}_init",
            callback=self._on_startup,
            priority=50,
        )
        api.register_shutdown_hook(
            hook_name="{plugin_id_us}_shutdown",
            callback=self._on_shutdown,
            priority=50,
        )
        logger.info("[{plugin_id}] hooks registered")

    async def _on_startup(self):
        logger.info("[{plugin_id}] starting up")

    async def _on_shutdown(self):
        logger.info("[{plugin_id}] shutting down")
'''

_ROUTERS_SETUP = '''\
# -*- coding: utf-8 -*-
"""Routers exposed by the {title} plugin."""


def build_plugin_routers():
    from .routers.health import router as health_router

    return [(health_router, "/{plugin_id}")]
'''

_HEALTH_ROUTER = '''\
# -*- coding: utf-8 -*-
"""GET /api/{plugin_id}/health — liveness check."""

from fastapi import APIRouter

router = APIRouter(prefix="", tags=["{plugin_id}"])


@router.get("/health")
def health() -> dict:
    return {{"status": "ok", "plugin": "{plugin_id}"}}
'''

_README = """\
# {title} Plugin

> **ID:** `{plugin_id}` · **Versão:** 0.1.0
> Gerado pelo AgentForge — preencha as TODOs antes de publicar.

## Instalação

1. O plugin já vive em `plugins/bundle/{plugin_id}/`.
2. Reinicie o backend JotaDuo — o hook `{plugin_id_us}_init` roda
   automaticamente.

## API

Prefixo: `/api/{plugin_id}`

- `GET /health` — liveness check.

## TODO

- [ ] Registrar agentes via `save_agent_config`
- [ ] Adicionar skills ao pool
- [ ] Plugar tools reais
- [ ] Escrever testes em `tests/unit/plugins/{plugin_id_us}/`
"""


async def scaffold_plugin(
    name: str,
    description: str,
    author: str = "AgentForge",
    target_dir: str = "plugins/bundle",
    min_version: str = "1.1.7",
    dry_run: bool = True,
):
    """Generate a minimal JotaDuo plugin bundle.

    Args:
        name: Plugin display name. Folder slug derives via kebab().
        description: Single-paragraph description for the manifest.
        author: Author field for plugin.json.
        target_dir: Parent under which the bundle is created.
        min_version: Minimum JotaDuo version supported.
        dry_run: If True, returns plan only.
    """
    if not name.strip():
        return text_response("ERROR: name vazio")
    if not description.strip():
        return text_response("ERROR: description vazio")

    plugin_id = kebab(name)
    plugin_id_us = slugify(name)
    class_name = "".join(part.capitalize() for part in plugin_id_us.split("_"))
    if not class_name.endswith("Plugin"):
        class_name = f"{class_name}Plugin"
    title = name.strip()
    folder = f"{target_dir.rstrip('/')}/{plugin_id}"

    manifest = {
        "id": plugin_id,
        "name": title,
        "version": "0.1.0",
        "type": "general",
        "description": description.strip(),
        "author": author.strip() or "AgentForge",
        "entry": {"backend": "plugin.py"},
        "dependencies": ["fastapi>=0.110", "pydantic>=2.0"],
        "min_version": min_version,
        "meta": {
            "category": "generated",
            "features": ["http-api-router"],
        },
    }

    plan = [
        {
            "path": f"{folder}/plugin.json",
            "content": json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
        },
        {
            "path": f"{folder}/__init__.py",
            "content": (
                "# -*- coding: utf-8 -*-\n"
                f'"""Public re-exports for the {plugin_id} plugin."""\n\n'
                f'__all__ = ["{class_name}"]\n\n'
                "def __getattr__(name):  # pragma: no cover\n"
                f'    if name == "{class_name}":\n'
                f"        from .plugin import {class_name}\n\n"
                f"        return {class_name}\n"
                "    raise AttributeError(name)\n"
            ),
        },
        {
            "path": f"{folder}/plugin.py",
            "content": _PLUGIN_PY.format(
                title=title,
                class_name=class_name,
                plugin_id=plugin_id,
                plugin_id_us=plugin_id_us,
            ),
        },
        {
            "path": f"{folder}/routers_setup.py",
            "content": _ROUTERS_SETUP.format(
                title=title,
                plugin_id=plugin_id,
            ),
        },
        {
            "path": f"{folder}/routers/__init__.py",
            "content": (
                "# -*- coding: utf-8 -*-\n"
                "from . import health\n\n"
                '__all__ = ["health"]\n'
            ),
        },
        {
            "path": f"{folder}/routers/health.py",
            "content": _HEALTH_ROUTER.format(plugin_id=plugin_id),
        },
        {
            "path": f"{folder}/README.md",
            "content": _README.format(
                title=title,
                plugin_id=plugin_id,
                plugin_id_us=plugin_id_us,
            ),
        },
    ]

    payload: dict = {
        "kind": "plugin",
        "plugin_id": plugin_id,
        "class_name": class_name,
        "folder": folder,
        "files": [
            {"path": entry["path"], "bytes": len(entry["content"])}
            for entry in plan
        ],
        "dry_run": dry_run,
    }
    if not dry_run:
        payload["written"] = write_files(plan)
    return json_response(payload)
