# -*- coding: utf-8 -*-
"""Component manifest tests.

For every entry in ``components/manifest.json`` there must exist a TSX
file that uses CopilotKit's ``useCoAgentStateRender`` (so the contract
between the Python adapter and the React renderers is enforced).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from copilotkit_adapter import components_manifest

_PLUGIN_ROOT = Path(__file__).resolve().parents[4] / (
    "plugins/bundle/discovery-copilotkit"
)
_COMPONENTS_DIR = _PLUGIN_ROOT / "components"


def test_manifest_is_valid_json():
    manifest = components_manifest()
    assert manifest["agentId"] == "discovery"
    assert manifest["stateSchema"] == "DiscoveryAgentState"
    assert isinstance(manifest["components"], list)
    assert manifest["components"]


@pytest.mark.parametrize(
    "component",
    components_manifest()["components"],
    ids=lambda c: c["name"],
)
def test_component_file_exists(component: dict):
    f = _COMPONENTS_DIR / component["file"]
    assert f.exists(), f"missing {f}"
    content = f.read_text(encoding="utf-8")
    # Every renderer must import CopilotKit and bind via the CoAgent
    # state render hook — except the panel which uses CopilotKit's
    # provider directly.
    if component["name"] == "DiscoveryAgentPanel":
        assert "CopilotKit" in content
        assert "useCoAgent" in content
    else:
        assert "useCoAgentStateRender" in content
    # The component must export its main symbol.
    assert f"export function {component['name']}" in content or (
        f"export {{ {component['name']}" in content
    )


def test_types_ts_matches_python_state_keys():
    """Sanity: each Pydantic field of DiscoveryAgentState appears in
    the TS type. This is a loose textual check — it catches forgetting
    to mirror a Python field on the client without requiring a full
    TypeScript compiler in the test runner.
    """
    from copilotkit_adapter import DiscoveryAgentState

    ts_src = (_COMPONENTS_DIR / "types.ts").read_text(encoding="utf-8")
    for field_name in DiscoveryAgentState.model_fields.keys():
        assert field_name in ts_src, (
            f"types.ts is missing field {field_name!r} declared by the "
            f"Python DiscoveryAgentState"
        )


def test_index_reexports_every_component():
    manifest = components_manifest()
    index = (_COMPONENTS_DIR / "index.ts").read_text(encoding="utf-8")
    for c in manifest["components"]:
        assert c["name"] in index, (
            f"components/index.ts does not export {c['name']}"
        )


def test_plugin_json_declares_components_endpoint():
    data = json.loads((_PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
    meta = data["meta"]["copilotkit"]
    assert meta["agent_id"] == "discovery"
    assert meta["components_endpoint"].endswith("/components")
