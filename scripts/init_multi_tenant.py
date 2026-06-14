#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize multi-tenant permission data — idempotent, safe to re-run.

Actions:
  1. Clear old governance agent_policies / resource_policies (file mode)
  2. Initialize capability approval default configs (5 types)
  3. Initialize 4 built-in agent templates
  4. Clear existing agent_user_grants (fresh start)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from jotaduo.constant import SECRET_DIR


def _governance_path() -> Path:
    return Path(SECRET_DIR) / "jotaduo_governance.json"


def _grants_path() -> Path:
    return Path(SECRET_DIR) / "jotaduo_agent_grants.json"


def _approval_path() -> Path:
    return Path(SECRET_DIR) / "jotaduo_capability_approval.json"


def _templates_path() -> Path:
    return Path(SECRET_DIR) / "jotaduo_agent_templates.json"


def step1_clear_old_governance():
    """Clear agent_policies and resource_policies from governance JSON."""
    path = _governance_path()
    if not path.exists():
        print(f"  [SKIP] {path} does not exist")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False

    for key in ("agent_policies", "resource_policies"):
        if data.get(key):
            count = len(data[key])
            data[key] = {}
            changed = True
            print(f"  [CLEAR] {key}: removed {count} entries")
        else:
            print(f"  [OK] {key}: already empty")

    if changed:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  [SAVED] {path}")


def step2_clear_grants():
    """Clear all agent_user_grants for fresh start."""
    path = _grants_path()
    if not path.exists():
        print(f"  [SKIP] {path} does not exist")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    count = sum(len(v) for v in data.values()) if isinstance(data, dict) else 0
    path.write_text("{}", encoding="utf-8")
    print(f"  [CLEAR] agent grants: removed {count} entries")


def step3_init_approval_config():
    """Initialize capability approval defaults via the module."""
    from jotaduo_ext.jotaduo.capability_approval import (
        ensure_default_configs,
        list_configs,
    )

    ensure_default_configs()
    configs = list_configs()
    print(f"  [OK] {len(configs)} capability approval configs initialized:")
    for c in configs:
        print(
            f"       {c['capability_type']:8s} add={c['add_approval']} rm={c['remove_approval']} auto={c['auto_approve_remove']}"
        )


def step4_init_templates():
    """Initialize built-in templates via the module."""
    from jotaduo_ext.jotaduo.agent_templates import (
        ensure_builtin_templates,
        list_templates,
    )

    ensure_builtin_templates()
    templates = list_templates()
    builtin_count = sum(1 for t in templates if t.get("builtin"))
    print(f"  [OK] {len(templates)} templates ({builtin_count} built-in):")
    for t in templates:
        tag = "[builtin]" if t.get("builtin") else "[custom]"
        print(f"       {tag} {t['template_id']:20s} {t['name']}")


def main():
    print("=" * 60)
    print("Multi-tenant permission initialization")
    print("=" * 60)

    print(f"\nSECRET_DIR: {SECRET_DIR}\n")

    print("[Step 1] Clear old governance agent_policies / resource_policies")
    step1_clear_old_governance()

    print("\n[Step 2] Clear agent_user_grants")
    step2_clear_grants()

    print("\n[Step 3] Initialize capability approval configs")
    step3_init_approval_config()

    print("\n[Step 4] Initialize built-in agent templates")
    step4_init_templates()

    print("\n" + "=" * 60)
    print("Done. System is ready for multi-tenant operation.")
    print("=" * 60)


if __name__ == "__main__":
    main()
