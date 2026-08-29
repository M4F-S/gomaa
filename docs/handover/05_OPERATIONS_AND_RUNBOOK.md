# Operations & Maintenance Runbook 🛠️

---

## 1. Quick Operations CLI (`./scripts/vps.sh`)

Any operational task can be performed directly via `./scripts/vps.sh`:

```bash
# 1. Check VPS container health, databases, and agent tool registrations
./scripts/vps.sh status

# 2. Run runtime MCP health audit across all 5 agent containers
./scripts/vps.sh audit

# 3. Run full automated test suite inside hermes-agent container
./scripts/vps.sh test

# 4. Sync local codebase changes to VPS and install into all container venvs
./scripts/vps.sh sync

# 5. Restart all 5 Hermes agent containers
./scripts/vps.sh restart

# 6. Tail live logs for an agent container (e.g. hermes-agent, hermes-assistant)
./scripts/vps.sh logs hermes-agent

# 7. Execute command inside an agent container
./scripts/vps.sh shell hermes-agent "python -V"
```

---

## 2. Triggering Manual Ebbinghaus Consolidation

```bash
# On VPS host: runs decay engine across all databases
docker exec hermes-agent /opt/data/mcp-servers/venv/bin/python -m gomaa consolidate --decay-rate 0.95 --archive-threshold 0.05
```

---

## 3. PostgreSQL Database Backup Procedure

```bash
# Dump all agent databases to compressed SQL
docker exec mo-graphify-obsidian-memory-postgres-1 pg_dumpall -U mnemosyne > /root/backups/gomaa_all_$(date +%Y%m%d).sql
```

---

## 4. Google Drive Synchronization Operations

```bash
# One-off synchronization pass
gomaa sync-gdrive --folder "Hermes-Fleet-Vault" --credentials service-account.json

# Run as a continuous background daemon
gomaa sync-gdrive --daemon --interval 300 --folder "Hermes-Fleet-Vault"
```

---

## 5. Troubleshooting Common Issues

### Issue A: Telegram Flood Control / Rate Limit
* **Symptom:** Agent warns `Telegram flood control, waiting ...` in `errors.log`.
* **Action:** Telegram enforces a 1-message-edit/second throttle. The gateway buffers and recovers automatically. If stalled, restart the container via `./scripts/vps.sh restart`.

### Issue B: MCP Server Connection Closed
* **Symptom:** `Failed to connect to MCP server 'obsidian_memory'`.
* **Action:** Run `./scripts/vps.sh audit` to verify PostgreSQL container health (`mo-graphify-obsidian-memory-postgres-1`) and database connectivity.
