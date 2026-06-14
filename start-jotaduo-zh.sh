#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy

export JOTADUO_AUTH_ENABLED="${JOTADUO_AUTH_ENABLED:-true}"
export JOTADUO_DB_URL="${JOTADUO_DB_URL:-postgresql+psycopg2://jotaduo:jotaduo_dev_password@127.0.0.1:5432/jotaduo}"

# --- 100-user tuning ---
export JOTADUO_DB_POOL_SIZE="${JOTADUO_DB_POOL_SIZE:-10}"
export JOTADUO_DB_MAX_OVERFLOW="${JOTADUO_DB_MAX_OVERFLOW:-20}"
export JOTADUO_MAX_ACTIVE_AGENTS="${JOTADUO_MAX_ACTIVE_AGENTS:-50}"
export JOTADUO_AGENT_IDLE_TTL_SECONDS="${JOTADUO_AGENT_IDLE_TTL_SECONDS:-1800}"

exec .venv/bin/jotaduo app --host 127.0.0.1 --port "${JOTADUO_PORT:-8088}"
