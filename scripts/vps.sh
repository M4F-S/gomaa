#!/usr/bin/env bash
# ==============================================================================
# Mnemosyne Fleet VPS Management & Diagnostic CLI
# Connects directly to the production VPS (<YOUR_VPS_IP>)
# ==============================================================================

set -euo pipefail

VPS_HOST="${VPS_HOST:-root@<YOUR_VPS_IP>}"
CONTAINERS=("hermes-agent" "hermes-assistant" "hermes-marketing" "hermes-pentest" "hermes-trader")

SSH_CMD="ssh -o ConnectTimeout=10 -o BatchMode=yes $VPS_HOST"

usage() {
    echo "Usage: $0 {status|test|sync|restart|logs|audit|shell}"
    echo ""
    echo "Commands:"
    echo "  status         Check Docker containers, databases, and microservices"
    echo "  test           Run pytest suite inside live hermes-agent container"
    echo "  sync           Synchronize local codebase to VPS and install into agent venvs"
    echo "  restart        Restart all 5 Hermes agent containers"
    echo "  logs [agent]   Tail logs for an agent (default: hermes-agent)"
    echo "  audit          Run runtime MCP health audit across all 5 agents"
    echo "  shell [agent]  Open an interactive or one-off command in a container"
    exit 1
}

case "${1:-}" in
    status)
        echo "=== [1/3] VPS Docker Containers ==="
        $SSH_CMD "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
        echo ""
        echo "=== [2/3] PostgreSQL Fleet Databases ==="
        $SSH_CMD "docker exec -i \$(docker ps -q -f name=postgres) psql -U mnemosyne -d postgres -c '\l'" 2>/dev/null || true
        echo ""
        echo "=== [3/3] MCP Memory Server Status in Agent Logs ==="
        for c in "${CONTAINERS[@]}"; do
            echo -n "$c: "
            $SSH_CMD "docker exec $c grep -i 'registered.*obsidian_memory' /opt/data/logs/agent.log 2>/dev/null | tail -n 1" || echo "No log found"
        done
        ;;

    test)
        echo "=== Running Mnemosyne Test Suite on VPS ($VPS_HOST) ==="
        $SSH_CMD "
            docker exec hermes-agent rm -rf /tmp/tests
            docker cp /tmp/mnemosyne-repo/tests hermes-agent:/tmp/tests
            docker exec -e PYTHONPATH=/tmp/mnemosyne-repo -e MEMORY_DB_DSN='postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/toy_db' hermes-agent /opt/data/mcp-servers/venv/bin/pytest -p no:postgresql /tmp/tests -v
        "
        ;;

    sync)
        echo "=== [1/2] Syncing local repo to VPS /tmp/mnemosyne-repo ==="
        scp -r /Users/mohamedfathy/.gemini/antigravity/scratch/mnemosyne/* "$VPS_HOST:/tmp/mnemosyne-repo/"
        echo "=== [2/2] Installing package into all 5 container venvs ==="
        for c in "${CONTAINERS[@]}"; do
            echo "Installing into $c..."
            $SSH_CMD "
                docker exec $c rm -rf /tmp/mnemosyne-repo
                docker cp /tmp/mnemosyne-repo $c:/tmp/mnemosyne-repo
                docker exec $c /opt/data/mcp-servers/venv/bin/pip install -e /tmp/mnemosyne-repo --no-deps
            "
        done
        echo "Sync complete!"
        ;;

    restart)
        echo "=== Restarting all 5 Hermes agent containers ==="
        $SSH_CMD "docker restart ${CONTAINERS[*]}"
        echo "Restart complete!"
        ;;

    logs)
        AGENT="${2:-hermes-agent}"
        echo "=== Tailing logs for $AGENT ==="
        $SSH_CMD "docker exec $AGENT tail -n 50 /opt/data/logs/agent.log"
        ;;

    audit)
        echo "=== Running Memory MCP Runtime Audit Across Fleet ==="
        $SSH_CMD '
        for c in hermes-agent hermes-assistant hermes-marketing hermes-pentest hermes-trader; do
            echo "----------------------------------------------------"
            echo "Agent Container: $c"
            
            DB="toy_db"
            if [ "$c" = "hermes-assistant" ]; then DB="old_db"; fi
            if [ "$c" = "hermes-marketing" ]; then DB="candy_db"; fi
            if [ "$c" = "hermes-pentest" ]; then DB="pencil_db"; fi
            if [ "$c" = "hermes-trader" ]; then DB="trader_db"; fi

            docker exec -e MEMORY_DB_DSN="postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/$DB" -e MEMORY_SHARED_DSN="postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/shared_db" $c /opt/data/mcp-servers/venv/bin/python -c "
import os, json
from mnemosyne.mcp_server import MCPServer
server = MCPServer()
health = server._health()
print(\"  Version:\", health[\"server\"][\"version\"])
print(\"  Status:\", health[\"server\"][\"status\"])
print(\"  Backend:\", health[\"store\"][\"backend\"])
print(\"  Shared connected:\", health[\"store\"][\"shared_store\"])
print(\"  Tools count:\", len(server._get_tools()))
"
        done
        '
        ;;

    shell)
        AGENT="${2:-hermes-agent}"
        shift 2 || true
        CMD="${*:-bash}"
        $SSH_CMD "docker exec -it $AGENT $CMD"
        ;;

    *)
        usage
        ;;
esac
