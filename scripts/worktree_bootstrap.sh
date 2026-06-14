#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Bootstrap a worktree with shared runtime resources.

Usage:
  bash scripts/worktree_bootstrap.sh [--shared-dir <path>] [--force] [--skip-install] [--pr-config]

Options:
  --shared-dir <path>  Path to shared runtime directory (default: ../_shared)
  --force              Overwrite existing symlinks
  --skip-install       Skip pnpm install
  --pr-config          Use .codex/pr.toml for Codex configuration

Behavior:
1) Links:
   - .env    -> <shared-dir>/env/qwenpaw.env
   - tenants -> <shared-dir>/tenants
   - uploads -> <shared-dir>/uploads
2) Runs pnpm install --prefer-offline (root package.json, or console/ fallback)
3) If --pr-config: Sets up .codex environment for PR review workflows
EOF
}

shared_dir="../_shared"
force=0
skip_install=0
pr_config=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --shared-dir)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for --shared-dir" >&2
                exit 1
            fi
            shared_dir="$2"
            shift 2
            ;;
        --force)
            force=1
            shift
            ;;
        --skip-install)
            skip_install=1
            shift
            ;;
        --pr-config)
            pr_config=1
            shift
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

create_link() {
    local source_path="$1"
    local target_path="$2"

    if [[ ! -e "$source_path" ]]; then
        echo "Shared source not found: $source_path" >&2
        exit 1
    fi

    if [[ -L "$target_path" ]]; then
        local current_target
        current_target="$(readlink "$target_path" || true)"
        if [[ "$current_target" == "$source_path" ]]; then
            return
        fi
        if [[ "$force" -eq 1 ]]; then
            rm -f "$target_path"
        else
            echo "Target already exists as another symlink: $target_path" >&2
            echo "Use --force to replace it." >&2
            exit 1
        fi
    elif [[ -e "$target_path" ]]; then
        if [[ "$force" -eq 1 ]]; then
            rm -rf "$target_path"
        else
            echo "Target already exists and is not a symlink: $target_path" >&2
            echo "Use --force to replace it." >&2
            exit 1
        fi
    fi

    ln -s "$source_path" "$target_path"
}

echo ">> Linking shared resources"
create_link "$shared_dir/env/qwenpaw.env" ".env"
create_link "$shared_dir/tenants" "tenants"
create_link "$shared_dir/uploads" "uploads"

if [[ "$skip_install" -eq 1 ]]; then
    echo ">> Skipping pnpm install (--skip-install)"
else
    echo ">> Installing JS dependencies (prefer offline)"
    if [[ -f "package.json" ]]; then
        pnpm install --prefer-offline
    elif [[ -f "console/package.json" ]]; then
        pnpm --dir console install --prefer-offline
    else
        echo "No package.json found in root or console/. Skipping pnpm install."
    fi
fi

if [[ "$pr_config" -eq 1 ]]; then
    echo ">> Setting up Codex PR configuration"
    if [[ -f ".codex/pr.toml" ]]; then
        export CODEX_CONFIG=".codex/pr.toml"
        echo "✓ CODEX_CONFIG set to .codex/pr.toml"
        echo "  Use --codex-config .codex/pr.toml with Codex CLI for PR reviews"
    else
        echo "⚠ .codex/pr.toml not found" >&2
    fi
fi
