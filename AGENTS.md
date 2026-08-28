# 🧠 Gomaa Autonomous Agent Ecosystem & VPS Operations Guide

> **Notice for all AI Coding Assistants (Antigravity, Cursor, Claude Code, Codex, Windsurf):**
> This repository is the source code and orchestration center for **Gomaa v3.5.0** and the 5-agent Hermes fleet deployed on a production VPS.
> Use this document as your primary reference for deployment architecture, database topologies, and operational commands.
> **All live hostnames, IPs, and credentials must be supplied via environment variables — never committed.**

---

## 🌐 Production VPS Infrastructure

| Resource | Value / Configuration |
|---|---|
| **VPS IP Address** | `` `${VPS_HOST}` `` |
| **SSH User** | `` `${VPS_USER:-root}` `` |
| **Direct SSH Command** | `` `ssh -o ConnectTimeout=10 -o BatchMode=yes ${VPS_USER:-root}@${VPS_HOST}` `` |
| **SSH Aliases** | `ssh ai-club-vps` or `ssh my-vps` (add your own in `~/.ssh/config`) |
| **Local SSH Key** | Configure your own in `~/.ssh/` (e.g. `~/.ssh/id_ed25519`) |
| **PostgreSQL Internal IP** | `` `${DB_HOST}:${DB_PORT}` `` (Docker network) |
| **Database Credentials** | User: `` `${DB_USER}` ``, Password: `` `${DB_PASSWORD}` `` |

---

## 🤖 The 5-Agent Hermes Fleet (per-agent memory databases)

Each agent container owns an isolated `pgvector` memory database. DSNs are `postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}`.

| Container Name | Agent Name | Domain / Role | Private Database Name | Vault Path |
|---|---|---|---|---|
| `hermes-agent` | Toy | Chief Orchestrator & Lead Researcher | `${DB_NAME_PREFIX}_toy` | `${VAULT_PATH}` |
| `hermes-assistant` | Old | Executive Task Manager & Personal Ops | `${DB_NAME_PREFIX}_old` | `${VAULT_PATH}` |
| `hermes-marketing` | Candy | Content Pipeline & Social Marketing | `${DB_NAME_PREFIX}_candy` | `${VAULT_PATH}` |
| `hermes-pentest` | Pencil | Security Auditing | `${DB_NAME_PREFIX}_pencil` | `${VAULT_PATH}` |
| `hermes-trader` | Coin | Crypto & Market Quantitative Intelligence | `${DB_NAME_PREFIX}_trader` | `${VAULT_PATH}` |
| **Cross-Agent Shared** | Fleet | Global Knowledge & Threat Intelligence | `${DB_NAME_PREFIX}_shared` | *Shared DB* |

> **Security:** these table/DB names are illustrative. The real names, ports, and credentials are read from env vars / `.env` at deploy time.

---

## ⚡ Quick Operations CLI (`./scripts/vps.sh`)

A dedicated operations tool is located at [`scripts/vps.sh`](scripts/vps.sh). Any session can execute these commands directly (values come from env, never hardcoded):

```bash
# 1. Check container health, databases, and memory registrations
./scripts/vps.sh status

# 2. Run runtime MCP health audit across all agents
./scripts/vps.sh audit

# 3. Run the automated test suite inside a target container
./scripts/vps.sh test

# 4. Sync local codebase changes to the VPS deployment dir
./scripts/vps.sh sync

# 5. Restart all agent containers
./scripts/vps.sh restart

# 6. Tail live logs for an agent container
./scripts/vps.sh logs <agent>

# 7. Execute a command inside an agent container
./scripts/vps.sh shell <agent> "python -V"
```

See `.env.example` for the variables you must set before running any VPS command.

---

## 🛠️ Gomaa MCP Tool Reference (9 Tools)

All agents expose these MCP tools (under the `mcp__obsidian_memory__` prefix):

1. `memory_remember(title, content, tags, wing, room, salience, pinned)` — store hierarchical notes in Obsidian vault + pgvector; `pinned=True` resists Ebbinghaus decay.
2. `memory_publish_shared(title, content, tags, wing, room)` — publish sanitized findings to shared fleet memory (regex cred screening).
3. `memory_recall(query, mode, top_k, scope, include_shared)` — hybrid RRF search over private + shared stores.
4. `memory_assemble_context(query, max_tokens, scope, mode)` — retrieve and assemble token-budgeted prompt context block.
5. `memory_ingest_session(transcript, wing, room)` — turn-based transcript ingestion with sliding-window chunking.
6. `memory_timeline(limit)` — chronological audit trail.
7. `memory_history(title, limit)` — note version history & diffs.
8. `memory_remind_me(title, trigger_at, content, recurring)` — prospective reminder engine.
9. `memory_audit()` — real-time system health & backend statistics.

---

## 📚 Master Handover Dossier

Architecture, security policies, and runbooks live in [`docs/handover/`](docs/handover/):
- `00_INDEX_AND_EXECUTIVE_SUMMARY.md` — mission & roadmap
- `01_FLEET_ARCHITECTURE_AND_PORTS.md` — port assignments & layout
- `02_TECHNICAL_SPECIFICATION_V3.1.md` — RRF ranking & decay math
- `03_AGENT_INTEGRATIONS_CATALOG.md` — skill catalogs & MCP definitions
- `04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md` — growth plan
- `05_OPERATIONS_AND_RUNBOOK.md` — VPS runbook & recovery