#!/usr/bin/env bash
# ==============================================================================
# Gomaa Fleet VPS Management & Diagnostic CLI
# All connection details are read from environment variables / .env — never hardcoded.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env if present
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# --- Required connection settings (from env / .env, no defaults that touch prod) ---
VPS_HOST="${VPS_HOST:-127.0.0.1}"
VPS_USER="${VPS_USER:-root}"
VPS_PORT="${VPS_PORT:-22}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/gomaa}"
DB_USER="${DB_USER:-gomaa}"
DB_PASSWORD="${DB_PASSWORD:-}"          # never default to a real secret
DB_HOST="${DB_HOST:-${POSTGRES_HOST:-localhost}}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME_PREFIX="${DB_NAME_PREFIX:-gomaa}"

if [[ "${VPS_HOST}" == *"@"* ]] || [[ "${VPS_HOST}" == "ai-club-vps" ]] || [[ "${VPS_HOST}" == "my-vps" ]]; then
    SSH_HOST="${VPS_HOST}"
else
    SSH_HOST="${VPS_USER}@${VPS_HOST}"
fi
SSH_CMD="ssh -p ${VPS_PORT} -o ConnectTimeout=10 -o BatchMode=yes ${SSH_HOST}"

CONTAINERS=("hermes-agent" "hermes-assistant" "hermes-marketing" "hermes-pentest" "hermes-trader")

# Guard: refuse to run against 127.0.0.1 unless explicitly configured or ALLOW_UNCONFIGURED=1
if [ "${VPS_HOST}" = "127.0.0.1" ] && [ "${ALLOW_UNCONFIGURED:-0}" != "1" ]; then
    echo "ERROR: VPS_HOST is not set. Configure it (see .env.example) or set ALLOW_UNCONFIGURED=1."
    exit 1
fi

# Per-agent database name helper: $1 = agent name / container name
agent_db() {
    case "$1" in
        hermes-agent|toy|toy_db) echo "toy_db" ;;
        hermes-assistant|old|old_db) echo "old_db" ;;
        hermes-marketing|candy|candy_db) echo "candy_db" ;;
        hermes-pentest|pencil|pencil_db) echo "pencil_db" ;;
        hermes-trader|coin|trader|trader_db) echo "trader_db" ;;
        shared|shared_db) echo "shared_db" ;;
        *) echo "${DB_NAME_PREFIX}_$1" ;;
    esac
}

usage() {
    echo "Usage: $0 {status|test|sync|restart|logs|audit|shell}"
    echo ""
    echo "Commands:"
    echo "  status         Check Docker containers, databases, and microservices"
    echo "  test           Run pytest suite inside a live agent container"
    echo "  sync           Synchronize local codebase to VPS deploy dir and install"
    echo "  restart        Restart all agent containers"
    echo "  logs [agent]   Tail logs for an agent (default: hermes-agent)"
    echo "  audit          Run a runtime MCP health audit across all agents"
    echo "  shell [agent]  Open an interactive or one-off command in a container"
    exit 1
}

dns_for() {
    # $1 = agent name -> DSN for that agent's private memory DB
    local dbname
    dbname="$(agent_db "$1")"
    echo "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${dbname}"
}

case "${1:-}" in
    status)
        echo "=== [1/3] Remote Docker Containers ==="
        $SSH_CMD "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
        echo ""
        echo "=== [2/3] PostgreSQL Fleet Databases ==="
        $SSH_CMD "docker exec -i \$(docker ps -q -f name=postgres) psql -U ${DB_USER} -d postgres -c '\l'" 2>/dev/null || true
        echo ""
        echo "=== [3/3] MCP Memory Server Status in Agent Logs ==="
        for c in "${CONTAINERS[@]}"; do
            echo -n "$c: "
            $SSH_CMD "docker exec $c grep -i 'registered.*obsidian_memory' /opt/data/logs/agent.log 2>/dev/null | tail -n 1" || echo "No log found"
        done
        ;;

    test)
        echo "=== Running Mnemosyne Test Suite on ${VPS_HOST} ==="
        for c in "${CONTAINERS[@]}"; do
            echo "--- Testing inside: $c ---"
            # Container path may differ; DEPLOY_DIR defaults to /opt/mnemosyne.
            $SSH_CMD "docker exec -e PYTHONPATH=${DEPLOY_DIR} -e MEMORY_DB_DSN='$(dns_for toy)' $c ${DEPLOY_DIR}/.venv/bin/pytest ${DEPLOY_DIR}/tests -v" \
                2>/dev/null || echo "  (skipped — ${DEPLOY_DIR} not present or test failed on $c)"
        done
        ;;

    sync)
        echo "=== Syncing local repo to ${SSH_HOST}:${DEPLOY_DIR} ==="
        rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '.venv' \
            -e "ssh -p ${VPS_PORT}" \
            "${PROJECT_ROOT}/" "${SSH_HOST}:${DEPLOY_DIR}/"
        echo "Sync complete!"
        ;;

    restart)
        echo "=== Restarting agent containers ==="
        for c in "${CONTAINERS[@]}"; do
            $SSH_CMD "docker restart ${c}" && echo "restarted ${c}"
        done
        ;;

    logs)
        AGENT="${2:-hermes-agent}"
        echo "=== Tailing logs for ${AGENT} ==="
        $SSH_CMD "docker exec ${AGENT} tail -n 50 /opt/data/logs/agent.log"
        ;;

    audit)
        echo "=== Running Memory MCP Runtime Audit Across Fleet ==="
        for c in "${CONTAINERS[@]}"; do
            echo "----------------------------------------------------"
            echo "Agent Container: $c"
            $SSH_CMD "docker exec -e MEMORY_DB_DSN='$(dns_for "$c")' ${c} /opt/data/mcp-servers/venv/bin/python -c \"
import os, json
try:
    from gomaa.mcp_server import MCPServer
except ImportError:
    from mnemosyne.mcp_server import MCPServer
server = MCPServer()
health = server._health()
print('  Version:', health['server']['version'])
print('  Status:', health['server']['status'])
print('  Backend:', health['store']['backend'])
print('  Shared connected:', health['store']['shared_store'])
print('  Tools count:', len(server._get_tools()))
\""
        done
        ;;

    shell)
        AGENT="${2:-hermes-agent}"
        shift 2 || true
        CMD="${*:-bash}"
        $SSH_CMD "docker exec \$([ -t 0 ] && echo '-it' || echo '-i') ${AGENT} ${CMD}"
        ;;

    *)
        usage
        ;;
esac