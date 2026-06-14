#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Create a feature worktree wired to shared runtime files.

Usage:
  bash scripts/worktree_feature.sh <feature-name> [--shared-dir <path>] [--force] [--pr-config]

Examples:
  bash scripts/worktree_feature.sh login-page
  bash scripts/worktree_feature.sh feature/login-page --shared-dir ../_shared
  bash scripts/worktree_feature.sh bugfix/auth --pr-config

Behavior:
1) git fetch origin
2) git worktree add -b feature/<name> ../<repo>-<name> origin/main
3) Creates links in the new worktree:
   - .env    -> <shared-dir>/env/qwenpaw.env
   - tenants -> <shared-dir>/tenants
   - uploads -> <shared-dir>/uploads
4) Runs pnpm install --prefer-offline (root package.json, or console/ fallback)
5) If --pr-config: Sets up Codex PR configuration
6) git push -u origin feature/<name>
EOF
}

shared_dir="../_shared"
force=0
feature_input=""
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
        --pr-config)
            pr_config=1
            shift
            ;;
        *)
            if [[ -z "$feature_input" ]]; then
                feature_input="$1"
                shift
            else
                echo "Unexpected extra argument: $1" >&2
                usage
                exit 1
            fi
            ;;
    esac
done

if [[ -z "$feature_input" ]]; then
    usage
    exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

repo_name="$(basename "$repo_root")"

if [[ "$feature_input" == feature/* ]]; then
    branch_name="$feature_input"
    feature_slug="${feature_input#feature/}"
else
    branch_name="feature/$feature_input"
    feature_slug="$feature_input"
fi

if [[ -z "$feature_slug" ]]; then
    echo "Feature name cannot be empty." >&2
    exit 1
fi

feature_slug="${feature_slug// /-}"
worktree_dir="../${repo_name}-${feature_slug//\//-}"

echo ">> Fetching origin"
git fetch origin

echo ">> Creating worktree: $worktree_dir ($branch_name from origin/main)"
git worktree add -b "$branch_name" "$worktree_dir" origin/main

cd "$worktree_dir"

echo ">> Bootstrapping shared links/dependencies"
bootstrap_args=(--shared-dir "$shared_dir")
if [[ "$force" -eq 1 ]]; then
    bootstrap_args+=(--force)
fi
if [[ "$pr_config" -eq 1 ]]; then
    bootstrap_args+=(--pr-config)
fi
bash scripts/worktree_bootstrap.sh "${bootstrap_args[@]}"

echo ">> Pushing branch to origin"
git push -u origin "$branch_name"

echo ""
echo "Worktree ready:"
echo "  Branch:   $branch_name"
echo "  Path:     $worktree_dir"
echo "  Shared:   $shared_dir"
if [[ "$pr_config" -eq 1 ]]; then
    echo "  Codex:    .codex/pr.toml (set)"
    echo ""
    echo "For PR review with Codex:"
    echo "  cd $worktree_dir && codex --config .codex/pr.toml"
fi
