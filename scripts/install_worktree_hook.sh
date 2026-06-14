#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

git config core.hooksPath .githooks

chmod +x .githooks/post-checkout
chmod +x scripts/worktree_bootstrap.sh
chmod +x scripts/worktree_feature.sh

echo "Git hook installed."
echo "hooksPath: $(git config --get core.hooksPath)"
echo ""
echo "Now every checkout to feature/* runs automatic bootstrap:"
echo "  - shared links (.env, tenants, uploads)"
echo "  - pnpm install --prefer-offline"
