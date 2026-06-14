#!/bin/sh
# Substitute JOTADUO_PORT in supervisord template and start supervisord.
# Default port 8088; override at runtime with -e JOTADUO_PORT=3000.
set -e

is_auth_enabled() {
  if [ "${JOTADUO_AUTH_ENABLED+x}" ]; then
    flag="${JOTADUO_AUTH_ENABLED}"
  else
    flag="${COPAW_AUTH_ENABLED:-}"
  fi
  flag="$(printf '%s' "$flag" | tr '[:upper:]' '[:lower:]')"
  [ "$flag" = "true" ] || [ "$flag" = "1" ] || [ "$flag" = "yes" ]
}

warn_if_auth_off_container_bind() {
  if is_auth_enabled; then
    return
  fi

  cat >&2 <<EOF
============================================================
SECURITY NOTICE: JotaDuo is running in Docker without authentication.

JotaDuo cannot verify whether access to the service is limited to a trusted
network. Anyone who can reach the service may access JotaDuo APIs without login.

Recommended:
  - Restrict access to a trusted network or protected environment.
  - Enable authentication with JOTADUO_AUTH_ENABLED=true if untrusted users or
    processes may reach the service.
============================================================
EOF
}

# Auto-initialize if config.json is missing (bind mount with empty directory).
if [ ! -f "${JOTADUO_WORKING_DIR}/config.json" ]; then
    echo "No config.json found in ${JOTADUO_WORKING_DIR}"
    echo "Executando inicialização do Jotaduo..."
    jotaduo init --defaults --accept-security
    echo "Inicialização concluída."
else
  echo "Configuração encontrada em ${JOTADUO_WORKING_DIR}, ignorando inicialização."
fi

# Run Alembic migrations if JOTADUO_DB_URL is set.
if [ -n "${JOTADUO_DB_URL:-}" ]; then
    echo "Executando migrações do banco de dados..."
    if alembic upgrade head; then
        echo "Migrações do banco de dados concluídas."
    else
        echo "AVISO: Falha na migração do banco de dados. As tabelas podem ser criadas no primeiro acesso." >&2
    fi
fi

export JOTADUO_PORT="${JOTADUO_PORT:-8088}"
warn_if_auth_off_container_bind
envsubst '${JOTADUO_PORT}' \
  < /etc/supervisor/conf.d/supervisord.conf.template \
  > /etc/supervisor/conf.d/supervisord.conf
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
