# 🧠 Mnemosyne Autonomous Agent Ecosystem & VPS Operations Guide

> **Notice for all AI Coding Assistants (Antigravity, Cursor, Claude Code, Codex, Windsurf):**
> This repository is the source code and orchestration center for **Mnemosyne v3.3.0** and the 5-agent Hermes fleet deployed on the production VPS.
> Use this document as your primary reference for VPS access, architecture, database topologies, and operational commands.

---

## 🌐 Production VPS Infrastructure

| Resource | Value / Configuration |
|---|---|
| **VPS IP Address** | `<YOUR_VPS_IP>` |
| **SSH User** | `root` |
| **Direct SSH Command** | `ssh -o ConnectTimeout=10 -o BatchMode=yes root@<YOUR_VPS_IP>` |
| **SSH Aliases** | `ssh ai-club-vps` or `ssh my-vps` |
| **Local SSH Key** | Automatically configured at `~/.ssh/id_vps` & `~/.ssh/id_ed25519_ai_club` |
| **PostgreSQL Internal IP** | `<POSTGRES_INTERNAL_IP>:5432` (Docker network `hermes-net`) |
| **Database Credentials** | User: `mnemosyne`, Password: `mnemosyne` |

---

## 🤖 The 5 Production Hermes Agent Containers

| Container Name | Agent Name | Domain / Role | Private Database DSN | Vault Path |
|---|---|---|---|---|
| **`hermes-agent`** | **Toy** | Chief Orchestrator & Lead Researcher | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/toy_db` | `/opt/data/vault` |
| **`hermes-assistant`** | **Old** | Executive Task Manager & Personal Ops | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/old_db` | `/opt/data/obsidian-vault` |
| **`hermes-marketing`** | **Candy** | Content Pipeline & Social Marketing | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/candy_db` | `/opt/data/obsidian-vault` |
| **`hermes-pentest`** | **Pencil** | Security Auditing (154 Hexstrike tools) | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/pencil_db` | `/opt/data/obsidian-vault` |
| **`hermes-trader`** | **Coin** | Crypto & Market Quantitative Intelligence | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/trader_db` | `/opt/data/obsidian-vault` |
| **Cross-Agent Shared** | **Fleet** | Global Knowledge & Threat Intelligence | `postgresql://<DB_USER>:<DB_PASSWORD>@<POSTGRES_INTERNAL_IP>:5432/shared_db` | *Shared DB* |

---

## ⚡ Quick Operations CLI (`./scripts/vps.sh`)

A dedicated operations tool is located at [`scripts/vps.sh`](scripts/vps.sh). Any session can execute these commands directly:

```bash
# 1. Check VPS container health, databases, and memory registrations
./scripts/vps.sh status

# 2. Run runtime MCP health audit across all 5 agents
./scripts/vps.sh audit

# 3. Run full automated test suite (52 tests) inside hermes-agent container
./scripts/vps.sh test

# 4. Sync local codebase changes to VPS and install into all container venvs
./scripts/vps.sh sync

# 5. Restart all 5 Hermes agent containers
./scripts/vps.sh restart

# 6. Tail live logs for an agent container (e.g. hermes-agent, hermes-trader)
./scripts/vps.sh logs hermes-agent

# 7. Execute command inside an agent container
./scripts/vps.sh shell hermes-agent "python -V"
```

---

## 🛠️ Mnemosyne v3.3.0 Tool Reference (8 Tools)

All 5 agents have the following 8 MCP tools available under the `mcp__obsidian_memory__` prefix:

1. **`memory_remember(title, content, tags, wing, room, salience, pinned)`**
   * Stores hierarchical notes in Obsidian vault + PostgreSQL `pgvector`.
   * `pinned=True` grants permanent immunity to Ebbinghaus temporal decay.
2. **`memory_publish_shared(title, content, tags, wing, room)`**
   * Publishes vetted policies/findings to `shared_db` with regex credential screening.
3. **`memory_recall(query, mode, top_k, scope, include_shared)`**
   * Hybrid RRF search querying both private store and cross-agent shared fleet store.
4. **`memory_ingest_session(transcript, wing, room)`**
   * Ingests turn-based transcripts with sliding-window linear chunking for turns >1,500 chars.
5. **`memory_timeline(limit)`**
   * Chronological audit trail of all memory operations.
6. **`memory_history(title, limit)`**
   * Note version history and diffs.
7. **`memory_remind_me(title, trigger_at, content, recurring)`**
   * Prospective reminder engine.
8. **`memory_audit()`**
   * Real-time system health and backend statistics.

---

## 📚 Master Handover Dossier

Detailed architectural blueprints, security policies, and deployment runbooks are maintained in [`docs/handover/`](docs/handover/):
* `00_INDEX_AND_EXECUTIVE_SUMMARY.md` — Project mission & roadmap
* `01_FLEET_ARCHITECTURE_AND_PORTS.md` — Port assignments, container layout & cron jobs
* `02_TECHNICAL_SPECIFICATION_V3.1.md` — Math formulation, RRF ranking, decay algorithms
* `03_AGENT_INTEGRATIONS_CATALOG.md` — Skill catalogs & MCP definitions
* `04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md` — Growth & distribution plan
* `05_OPERATIONS_AND_RUNBOOK.md` — VPS runbook & incident recovery
