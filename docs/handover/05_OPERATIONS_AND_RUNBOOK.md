# Operations & Maintenance Runbook 🛠️

---

## 1. Quick Verification Commands (VPS Host)

```bash
# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Inspect Toy's live gateway log
docker exec hermes-agent tail -n 50 /opt/data/logs/gateway.log

# Inspect Toy's MCP tool discovery log
docker exec hermes-agent grep -i "obsidian_memory" /opt/data/logs/agent.log | tail -n 10

# Run full unit + PostgreSQL integration test suite
docker exec -e PYTHONPATH=/tmp hermes-agent /opt/data/mcp-servers/venv/bin/pytest -p no:postgresql /tmp/tests -v
```

---

## 2. Triggering Manual Ebbinghaus Consolidation

```bash
# On VPS host: runs decay engine across all 5 agent databases
python3 ${HOST_SCRIPTS_DIR}/nightly_consolidation.py
```

---

## 3. PostgreSQL Database Backup Procedure

```bash
# Dump all 5 agent databases to compressed SQL
docker exec mo-graphify-obsidian-memory-postgres-1 pg_dumpall -U mnemosyne > /root/backups/mnemosyne_all_$(date +%Y%m%d).sql
```

---

## 4. Troubleshooting Common Issues

### Issue A: Telegram Polling CLOSE-WAIT / Flood Control Hang
* **Symptom:** Agent stops responding on Telegram after sending a large message.
* **Fix:**
  ```bash
  docker restart hermes-agent
  ```

### Issue B: MCP Server Connection Closed
* **Symptom:** `Failed to connect to MCP server 'obsidian_memory'`.
* **Verification:** Ensure `MEMORY_DB_DSN` inside the container points to `postgresql://mnemosyne:***@${DB_HOST}:5432/<agent_db>`.
