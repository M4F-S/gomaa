# 🧠 Gomaa Autonomous Agent Ecosystem & VPS Operations Guide

> **Notice for all AI Coding Assistants (Antigravity, Cursor, Claude Code, Codex, Windsurf):**
> This repository is the source code and orchestration center for **Gomaa v4.0.0 ("Mnemosyne Neo")** and the 5-agent Hermes fleet deployed on a production VPS.
> Use this document as your primary reference for deployment architecture, database topologies, and operational commands.
> **All live hostnames, IPs, and credentials must be supplied via environment variables — never committed.**

---

## 🎯 Agent Operational Directives & Execution Protocol

### **Role & Objective**
Act as an expert researcher and strategic executioner. Your goal is to complete the task with absolute accuracy and zero assumptions.

### **Core Rules**
1. **Verify Everything:** Never assume facts, syntax, or outcomes. Treat every data point as unverified until proven otherwise.
2. **Research Deeply:** Conduct thorough research. Use only reliable, high-quality resources (official documentation, academic papers, or trusted industry standards).
3. **Test Continuously:** Run tests at every critical stage. Verify that code, logic, or data works in practice, not just in theory.

### **Execution Protocol**
1. **Research & Plan:** Investigate the problem deeply. Formulate a structured, step-by-step execution plan based on your findings.
2. **Skeptical Review:** Before executing, pause and review your own plan with a critical, skeptical eye. Identify potential edge cases, hidden flaws, or weak assumptions.
3. **Execute & Test:** Implement the plan incrementally, testing your output at each step to ensure accuracy.
4. **Git Workflow:** Work strictly within a Git repository. Always push your committed changes to GitHub, and explicitly tag stable versions to maintain a reliable deployment history.

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

## 🛠️ Gomaa MCP Tool Reference (13 Tools)

All agents expose these MCP tools (under the `mcp__obsidian_memory__` prefix):

1. `memory_remember(title, content, tags, wing, room, salience, pinned)` — store hierarchical notes in Obsidian vault + pgvector; `pinned=True` resists Ebbinghaus decay.
2. `memory_publish_shared(title, content, tags, wing, room)` — publish sanitized findings to shared fleet memory (regex cred screening).
3. `memory_recall(query, mode, top_k, scope, include_shared)` — hybrid RRF, semantic, keyword, 2-hop graph, HippoRAG `associative_ppr`, `procedural`, or `episodic` search over private + shared stores.
4. `memory_assemble_context(query, max_tokens, scope, mode)` — retrieve and assemble token-budgeted prompt context block.
5. `memory_ingest_session(transcript, wing, room)` — turn-based transcript ingestion with sliding-window chunking.
6. `memory_timeline(limit)` — chronological audit trail.
7. `memory_history(title, limit)` — note version history & diffs.
8. `memory_remind_me(title, trigger_at, content, recurring)` — prospective reminder engine.
9. `memory_ingest_event(session_id, stimulus, response, event_type, tool_name, tool_args, surprise_factor, outcome_status)` — log turn-level experiential episodes into the biological episodic ledger.
10. `memory_save_playbook(skill_name, domain, description, preconditions, tool_sequence, error_recovery)` — store/update procedural skill playbooks with Bayesian Laplace-smoothed utility tracking.
11. `memory_sleep(decay_factor, archive_threshold)` — trigger 3-phase biological sleep consolidation (SWS crystallization + REM playbook synthesis/latent link discovery + ATMS synaptic homeostasis).
12. `memory_working_buffer(action, session_id, agent_role, active_goal, subtask_stack, hypotheses, attention_window)` — manage Miller's Law ($7 \pm 2$) bounded working memory scratchpad.
13. `memory_audit()` — real-time system health & backend statistics.

---

## 🛡️ Core Engine Hardening & Architectural Guarantees (v4.0.0 - Mnemosyne Neo)

1. **4-Quadrant Cognitive Architecture:** Explicit separation of Episodic (`episodic_events`), Semantic (`notes` + `links`), Procedural (`procedural_playbooks`), and Working Memory (`working_memory`) stores across both SQLite and PostgreSQL.
2. **HippoRAG 2 Personalized PageRank (PPR):** Single-step multi-hop associative retrieval via power-iteration PPR ($K=20, \alpha=0.15$) with bi-directional forward/backlink traversal and ACT-R base-level activation boosting.
3. **3-Phase Biological Sleep Consolidation:** SWS high-surprise episode crystallization + procedural trajectory extraction, REM cross-agent playbook sharing + latent tag-bridge link discovery, and ATMS truth maintenance conflict resolution.
4. **Thread-Safe Atomic Vault Writes & DB Rollback Safety:** Writes use unique temporary sibling files (`.{name}.{pid}.{uuid}.tmp`) with pre-write backups to ensure zero vault corruption.
5. **Robust MCP Argument Coercion:** All 13 MCP tools gracefully coerce JSON-stringified arrays/dicts (`tags`, `preconditions`, `tool_sequence`, `error_recovery`, `scope`), comma-separated strings, and numeric strings into strongly typed Python primitives.
6. **Dual Storage Parity:** 100% feature parity between zero-config SQLite WAL local mode and production PostgreSQL 16 + pgvector (HNSW) fleet mode.

---

## 📚 Master Handover Dossier

Architecture, security policies, and runbooks live in [`docs/handover/`](docs/handover/):
- `00_INDEX_AND_EXECUTIVE_SUMMARY.md` — mission & roadmap
- `01_FLEET_ARCHITECTURE_AND_PORTS.md` — port assignments & layout
- `02_TECHNICAL_SPECIFICATION_V3.1.md` — RRF ranking & decay math
- `03_AGENT_INTEGRATIONS_CATALOG.md` — skill catalogs & MCP definitions
- `04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md` — growth plan
- `05_OPERATIONS_AND_RUNBOOK.md` — VPS runbook & recovery
- `07_GOMAA_V4_NEO_SPECIFICATION.md` — Gomaa v4.0 ("Mnemosyne Neo") specification

---

## 🧪 Current Verification & Health Status

* **Automated Tests:** 120 / 120 tests passing (100% success rate across 32 test modules, including LoCoMo/LongMemEval/HotpotQA benchmark harnesses).
* **Linter & Formatting:** 0 syntax/compilation errors across all modules.
* **VPS Production Fleet:** 5 agent containers (`hermes-agent`, `hermes-assistant`, `hermes-marketing`, `hermes-pentest`, `hermes-trader`) active, healthy, and synced with PostgreSQL + pgvector at `${DEPLOY_DIR}` (`/opt/gomaa`).