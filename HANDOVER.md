# 📁 Gomaa (v3.5.0) Handover & Quick Start

Welcome to the **Gomaa** long-term memory engine and Hermes agent fleet workspace.

For complete infrastructure specifications, container names, and VPS access commands, read:
👉 [**`AGENTS.md`**](AGENTS.md)
👉 [**`docs/handover/00_INDEX_AND_EXECUTIVE_SUMMARY.md`**](docs/handover/00_INDEX_AND_EXECUTIVE_SUMMARY.md)

### 🚀 Common One-Line Operations Commands

```bash
# Check fleet status, containers, and databases
./scripts/vps.sh status

# Run runtime MCP health audit across all 5 agents
./scripts/vps.sh audit

# Run the 94-item automated test suite locally
uv run pytest -v

# Sync local codebase changes to VPS deployment directory
./scripts/vps.sh sync

# Restart agent containers on VPS
./scripts/vps.sh restart
```

> All deployment values (hostnames, credentials) come from environment variables — see `.env.example`. They are never hardcoded in this repo.