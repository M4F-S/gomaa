# 📁 Mnemosyne Handover & Quick Start

Welcome to the **Mnemosyne** workspace.

For complete infrastructure specifications, container names, and VPS access commands, read:
👉 [**`AGENTS.md`**](AGENTS.md)
👉 [**`docs/handover/00_INDEX_AND_EXECUTIVE_SUMMARY.md`**](docs/handover/00_INDEX_AND_EXECUTIVE_SUMMARY.md)

### 🚀 Common One-Line Commands

```bash
# Check fleet status (set VPS_HOST/VPS_USER first — see .env.example)
./scripts/vps.sh status

# Run a MCP health audit across the fleet
./scripts/vps.sh audit

# Run the full test suite on a target container
./scripts/vps.sh test

# Sync local edits to the VPS deploy dir
./scripts/vps.sh sync
```

> All deployment values (host, credentials) come from environment variables — see `.env.example`. They are never hardcoded in this repo.