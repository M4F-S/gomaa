# Mnemosyne Project Master Plan
## Version: 1.1 | Date: July 7, 2026 | Status: Ready for Phase 0

---

## 1. PROJECT OVERVIEW

### 1.1 What We're Building

**Mnemosyne** — an open-core, local-first memory system for AI agents. It stores memories as plain Markdown files (Obsidian-compatible) with YAML frontmatter, uses PostgreSQL + pgvector for fast search, and exposes an MCP server for Claude/Cursor integration.

**Core philosophy:**
- Files are the source of truth (not the database)
- Works locally first (no cloud required)
- Incremental feature addition (ship core, then extend)
- Every feature is a plugin (microkernel architecture over time)

### 1.2 Current State

| Component | Status | File |
|-----------|--------|------|
| `UnifiedMemorySystem` core | ✅ Working | `scripts/mo_graphify_memory.py` (984 lines) |
| `VaultManager` (markdown I/O) | ✅ Working | `scripts/mo_graphify_memory.py` |
| `PgVectorStore` (PostgreSQL + pgvector) | ✅ Working | `scripts/mo_graphify_memory.py` |
| `Embedder` (3-tier fallback) | ✅ Working | `scripts/mo_graphify_memory.py` |
| `AdmissionControl` (security gate) | ✅ Working | `scripts/mo_graphify_memory.py` |
| `SalienceEngine` | ✅ Working | `scripts/mo_graphify_memory.py` |
| `ProspectiveMemory` (reminders) | ✅ Working | `scripts/mo_graphify_memory.py` |
| `ConsolidationEngine` | ✅ Working | `scripts/mo_graphify_memory.py` |
| `MemoryMCPServer` (MCP stdio) | ✅ Working | `scripts/mo_graphify_memory.py` |
| Backward compat (v1.0 functions) | ✅ Working | `scripts/mo_graphify_memory.py` |
| SKILL.md documentation | ✅ Working | `SKILL.md` |
| README.md | ✅ Working | `README.md` |
| SETUP.md | ✅ Working | `SETUP.md` |
| PostgreSQL + pgvector container | ✅ Running | Docker, port 15432 |
| Old Cognee files (deprecated) | ⚠️ In workspace | `workers/`, `ingestion/`, `demo/` |

### 1.3 Code Bugs Found (Must Fix in Phase 0)

| Bug | Severity | Location | Fix |
|-----|----------|----------|-----|
| **Race condition in `Embedder`** | 🔴 Critical | `embed()` never acquires `self._lock` | Add `with self._lock:` around model encoding |
| **MCP handler NameError** | 🔴 Critical | Exception handler uses `req` before defined | Use `req_id` variable, two-level try/except |
| **Unicode titles become `-.md`** | 🔴 Critical | `safe_filename` strips all non-ASCII | Use `unicodedata.normalize` |
| **Auto-sync crashes on fresh install** | 🔴 Critical | `__init__` calls `self.sync()` unconditionally | Make `auto_sync` optional (default False) |
| **Auto-init on import** | 🔴 Critical | Global singleton runs on every `import` | Remove auto-init, require explicit init |
| **`ivfflat` index (suboptimal)** | 🟡 High | Uses deprecated pgvector index | Change to `hnsw` (m=16, ef_construction=64) |
| **Missing `pgcrypto` extension** | 🟡 High | `gen_random_uuid()` requires it | Add `CREATE EXTENSION pgcrypto` |
| **Consolidation stats lie** | 🟡 Medium | Reports "merged: 0, pruned: 0" unimplemented | Remove from stats or implement |

### 1.4 Planning Gaps Fixed in v1.1

| Gap | Fix |
|-----|-----|
| No `develop` branch | Created `develop` branch from `main` |
| No test DB strategy | GitHub Actions `services:` with PostgreSQL + pgvector container |
| No `SKILL.md` update plan | Phase 0 includes updating all path references |
| No module splitting map | Exact mapping provided in Phase 0 prompt |
| `pyproject.toml` vs `setup.py` | `pyproject.toml` only (PEP 621) |
| No `Dockerfile` | Added to Phase 0 |
| No Python version matrix | Test on 3.9, 3.10, 3.11, 3.12 |
| No `CONTRIBUTING.md` | Added to Phase 0 |
| No `CHANGELOG.md` format | Keep a Changelog format |
| No `Makefile` targets | Exact targets specified in prompt |
| No `.gitignore` content | Explicit `.gitignore` provided in prompt |
| No `LICENSE` decision | Apache 2.0 |

---

## 2. SESSION MANAGEMENT STRATEGY

### 2.1 Why Separate Sessions?

**Context compression kills long-running sessions.** After 20-30 tool calls, the context window compresses and we lose critical details. **Separate sessions = fresh context = better quality code.**

**Session roles:**

| Role | Purpose | When to Spawn |
|------|---------|---------------|
| **Architect (This Session)** | Planning, decisions, review, audit, git management | Continuous |
| **Builder Session** | Write code, implement features, fix bugs | Per phase |
| **Test Session** | Write tests, run test suite, verify coverage | After each build |
| **Docs Session** | Write README, docs, examples, blog posts | After feature complete |
| **Research Session** | Market research, competitive analysis, tech evaluation | On demand |
| **Audit Session** | Code review, security audit, performance check | Before release |

### 2.2 Session Handoff Protocol

Every handoff between sessions must include:

```
HANDOFF TEMPLATE
================
1. PHASE COMPLETED: [What was built]
2. FILES MODIFIED: [List with git commit hashes]
3. DECISIONS MADE: [Key architectural choices]
4. ISSUES FOUND: [Bugs, edge cases, TODOs]
5. NEXT PHASE: [What to build next]
6. CONTEXT NEEDED: [What the next session must know]
7. TEST RESULTS: [Pass/fail, coverage %]
```

### 2.3 Builder Session Failure Protocol

If a builder session fails to produce working code:

1. Builder creates `HANDOFF.md` with failure reason
2. Architect reviews `HANDOFF.md` and decides:
   a. Re-spawn builder with corrected prompt (if fix is clear)
   b. Architect fixes directly (if simpler than re-spawning)
   c. Defer to next phase (if non-critical)
3. If 3 builder sessions fail on same task, architect re-evaluates scope

### 2.4 Memory Skill Usage for Persistence

The `mo-graphify-obsidian-memory` skill saves decisions to the vault. We use it to:

1. **Save architectural decisions** as markdown notes with `decision` type
2. **Save session summaries** as markdown notes with `session-log` type
3. **Save bug reports** as markdown notes with `bug` type
4. **Save feature specs** as markdown notes with `spec` type

**Example usage:**
```python
from mnemosyne import UnifiedMemorySystem
mem = UnifiedMemorySystem()
mem.remember(
    title="Decision: Use SQLite fallback for zero-config installs",
    content="We decided to add SQLite as a fallback database so users can try Mnemosyne without installing PostgreSQL. This reduces the barrier to entry. PostgreSQL remains the production choice.",
    tags=["decision", "architecture", "database"],
    salience=0.9
)
```

---

## 3. GIT WORKFLOW

### 3.1 Repository Structure

```
mo-graphify-obsidian-memory/     ← GitHub repo (github.com/M4F-S/mo-graphify-obsidian-memory)
├── .github/
│   ├── workflows/
│   │   └── ci.yml                 ← GitHub Actions (test on 3.9-3.12, lint, type-check)
│   ├── CONTRIBUTING.md            ← Contribution guidelines
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── pull_request_template.md
├── mnemosyne/                   ← Python package (was scripts/)
│   ├── __init__.py              ← Package init, version, exports
│   ├── core.py                  ← UnifiedMemorySystem
│   ├── stores/
│   │   ├── __init__.py
│   │   └── postgres.py          ← PgVectorStore
│   ├── embedder.py              ← Embedder
│   ├── vault.py                 ← VaultManager
│   ├── security.py              ← AdmissionControl, SalienceEngine
│   ├── prospective.py           ← ProspectiveMemory
│   ├── consolidation.py         ← ConsolidationEngine
│   ├── mcp_server.py            ← MemoryMCPServer
│   ├── compat.py                ← v1.0 backward compatibility functions
│   └── cli.py                   ← CLI entry point (placeholder)
├── tests/
│   ├── __init__.py
│   ├── test_core.py             ← Test UnifiedMemorySystem
│   ├── test_vault.py            ← Test VaultManager
│   ├── test_search.py           ← Test search modes
│   ├── test_mcp.py             ← Test MCP server
│   ├── test_integration.py     ← Integration tests (requires PostgreSQL)
│   └── conftest.py             ← pytest fixtures
├── docs/
│   ├── README.md                ← Main README (user-facing)
│   ├── SETUP.md                 ← Setup guide
│   ├── ARCHITECTURE.md          ← Architecture decisions
│   ├── ROADMAP.md               ← This file
│   ├── API.md                   ← API reference
│   └── reviews/                 ← Pre-build reviews and audits
│       └── review-001-pre-build-master-plan.md
├── examples/
│   ├── basic_usage.py           ← Simple example
│   ├── mcp_config.json          ← Claude Desktop config
│   └── docker-compose.yml       ← Docker setup
├── Dockerfile                   ← Mnemosyne app container
├── docker-compose.yml           ← Full stack (app + PostgreSQL)
├── requirements.txt             ← Dependencies
├── requirements-dev.txt         ← Dev dependencies (pytest, black, mypy)
├── pyproject.toml               ← Modern Python packaging (PEP 621, ONLY file)
├── Makefile                     ← Common commands (test, lint, format)
├── .gitignore                   ← Git ignore rules
├── LICENSE                      ← Apache 2.0
├── CHANGELOG.md                 ← Version history (Keep a Changelog format)
└── README.md                    ← Repo root README (GitHub landing page)
```

### 3.2 Branch Strategy

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Production-ready, stable | Protected, requires PR + review |
| `develop` | Integration branch for features | Protected, requires PR |
| `feature/*` | Individual features | Delete after merge |
| `hotfix/*` | Critical bug fixes | Fast-track to main |
| `docs/*` | Documentation updates | Can merge to develop |

**Note:** `develop` branch created from `main` on 2026-07-07. All feature branches branch from `develop`.

### 3.3 Commit Convention

```
<type>: <description>

<body>

Fixes #<issue>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `perf`

Examples:
- `feat: add SQLite fallback for zero-config installs`
- `fix: prevent auto-initialization on module import`
- `docs: update README with MCP configuration examples`
- `test: add pytest suite for vault manager`

### 3.4 Release Process

1. Create release branch from `develop`: `git checkout -b release/v1.1.0`
2. Update version in `__init__.py`, `pyproject.toml`, `CHANGELOG.md`
3. Run full test suite: `make test`
4. Create PR to `main`
5. After merge, tag: `git tag -a v1.1.0 -m "Release v1.1.0"`
6. Push tag: `git push origin v1.1.0`
7. GitHub Actions creates release automatically

### 3.5 Vault-to-GitHub Sync Protocol

After each phase, sync decisions from vault to repo:

```bash
# Copy new decisions from vault to repo
cp ~/Documents/Kimi/Workspaces/Mnemosyne/obsidian-vault/decisions/* docs/decisions/
cp ~/Documents/Kimi/Workspaces/Mnemosyne/obsidian-vault/sessions/* docs/sessions/

# Commit and push
git add docs/decisions/ docs/sessions/
git commit -m "docs: sync decisions and session logs from vault"
git push origin develop
```

---

## 4. PHASED BUILD PLAN

### Phase 0: Foundation (Week 1-2)
**Goal:** The repo is clean, installable, and tested.
**Deliverable:** `pip install -e .` works. Tests pass. CI is green.

**Tasks:**
1. Restructure repo (move `scripts/` to `mnemosyne/` package)
2. Add `__init__.py`, `requirements.txt`, `pyproject.toml` (PEP 621, ONLY packaging file)
3. Fix all 8 code bugs (race condition, NameError, Unicode, auto-init, etc.)
4. Add `Dockerfile` and `docker-compose.yml`
5. Add basic pytest test suite (10+ tests: unit + integration)
6. Add GitHub Actions CI with PostgreSQL service container
7. Test on Python 3.9, 3.10, 3.11, 3.12
8. Update README with correct installation instructions
9. Remove old Cognee files from workspace (archive to separate branch `archive/cognee-legacy`)
10. Fix SKILL.md references (remove `test_report.md`, fix paths)
11. Add `Makefile` with exact targets (help, install, test, test-integration, lint, format, check, clean)
12. Add `.gitignore` with explicit patterns
13. Add `LICENSE` (Apache 2.0)
14. Add `CHANGELOG.md` (Keep a Changelog format)
15. Add `CONTRIBUTING.md` and issue/PR templates
16. Git commit: `chore: restructure repo and add packaging`

**Session needed:** Builder session (restructure + packaging)
**Review needed:** Architect session (this one) reviews PR
**Test needed:** Test session runs full suite

**Exit criteria:**
- [ ] `pip install -e .` succeeds on fresh machine
- [ ] `pytest` passes 100% of unit tests
- [ ] `pytest tests/integration` passes with PostgreSQL
- [ ] GitHub Actions CI is green on all Python versions (3.9-3.12)
- [ ] `make lint` passes (flake8, mypy)
- [ ] `make check` passes (test + lint)
- [ ] No old Cognee files in workspace
- [ ] README installation instructions are accurate
- [ ] `docker-compose up` starts both app and PostgreSQL

---

### Phase 1: SQLite Fallback (Week 2-3)
**Goal:** Mnemosyne works without PostgreSQL for quick trials.
**Deliverable:** Zero-config install. PostgreSQL optional for production.

**Tasks:**
1. Add `SQLiteStore` class (implements same interface as `PgVectorStore`)
2. Add `sqlite-vec` or simple full-text search for SQLite
3. Modify `UnifiedMemorySystem` to auto-detect database (PostgreSQL preferred, SQLite fallback)
4. Update README: "Try without PostgreSQL!"
5. Add tests for SQLite path
6. Git commit: `feat: add SQLite fallback for zero-config installs`

**Session needed:** Builder session (SQLite implementation)
**Review needed:** Architect session reviews PR
**Test needed:** Test session tests both PostgreSQL and SQLite paths

**Exit criteria:**
- [ ] Works with `pip install -e .` (no PostgreSQL)
- [ ] `memory.remember()` and `memory.recall()` work with SQLite
- [ ] All tests pass for SQLite path
- [ ] PostgreSQL path still works (backward compat)

---

### Phase 2: MCP Server v2 (Week 3-4)
**Goal:** MCP server uses 2026-07-28 stateless spec. Works with Claude Desktop and Cursor.
**Deliverable:** Drop-in MCP server that any client can connect to.

**Tasks:**
1. Update `MemoryMCPServer` to 2026-07-28 stateless spec (no `initialize` handshake)
2. Add Streamable HTTP transport option (for remote MCP)
3. Add `mnemosyne-mcp` CLI entry point
4. Add `mcp_config.json` example for Claude Desktop
5. Add `mcp_config_cursor.json` example for Cursor
6. Test end-to-end with Claude Desktop (real end-to-end test)
7. Test end-to-end with Cursor (real end-to-end test)
8. Add tests for MCP server
9. Git commit: `feat: update MCP server to 2026-07-28 stateless spec`

**Session needed:** Builder session (MCP server update)
**Review needed:** Architect session reviews PR
**Test needed:** Test session tests MCP protocol compliance

**Exit criteria:**
- [ ] Claude Desktop can connect and use `memory_remember`
- [ ] Claude Desktop can connect and use `memory_recall`
- [ ] Cursor can connect and use both tools
- [ ] MCP server tests pass
- [ ] No `initialize` handshake required

---

### Phase 3: CLI Tool (Week 4-5)
**Goal:** Command-line interface for daily use.
**Deliverable:** `mnemosyne remember`, `mnemosyne recall`, `mnemosyne status`

**Tasks:**
1. Add `mnemosyne` CLI with argparse
2. Commands: `remember`, `recall`, `remind-me`, `consolidate`, `sync`, `status`, `mcp`
3. Add shell completion (bash, zsh)
4. Add `mnemosyne --version`
5. Add `mnemosyne --config` (show current config)
6. Add tests for CLI
7. Git commit: `feat: add CLI tool for memory management`

**Session needed:** Builder session (CLI implementation)
**Review needed:** Architect session reviews PR
**Test needed:** Test session tests CLI commands

**Exit criteria:**
- [ ] `mnemosyne remember "title" "content"` works
- [ ] `mnemosyne recall "query"` returns results
- [ ] `mnemosyne status` shows system health
- [ ] `mnemosyne --version` shows version
- [ ] All CLI tests pass

---

### Phase 4: VPS Deployment (Week 5-6)
**Goal:** MCP server runs on VPS for remote access.
**Deliverable:** `https://memory.yourdomain.com` — live MCP server.

**Tasks:**
1. Add FastAPI wrapper for MCP server (HTTP transport)
2. Add Docker Compose for VPS deployment (PostgreSQL + FastAPI + Nginx)
3. Add Nginx config (reverse proxy, Let's Encrypt)
4. Add simple auth (API key, not OAuth)
5. Deploy to VPS
6. Test remote connection from Claude Desktop
7. Add `docker-compose.yml` to repo
8. Add deployment docs
9. Git commit: `feat: add Docker deployment for VPS hosting`

**Session needed:** Builder session (Docker + FastAPI)
**Review needed:** Architect session reviews PR
**Test needed:** Test session tests Docker deployment locally

**Exit criteria:**
- [ ] Docker Compose runs locally without errors
- [ ] VPS deployment is accessible via HTTPS
- [ ] MCP client can connect remotely
- [ ] API key auth works
- [ ] Health endpoint returns OK

---

### Phase 5: Launch (Week 7-8)
**Goal:** Post on Hacker News, 42 Berlin, Reddit. Get first users.
**Deliverable:** 100 GitHub stars, 20 users.

**Tasks:**
1. Record 2-minute demo video
2. Write Hacker News post ("Show HN: Mnemosyne — local memory for AI assistants")
3. Post on 42 Berlin Slack
4. Post on r/selfhosted, r/ClaudeAI, r/ObsidianMD
5. Create simple website (GitHub Pages) with install guide
6. Respond to all comments/issues within 24 hours
7. Track metrics (stars, issues, discussions)
8. Git commit: `docs: add website and launch materials`

**Session needed:** Docs session (video, website, posts)
**Review needed:** Architect session reviews all public materials

**Exit criteria:**
- [ ] Demo video is under 2 minutes
- [ ] Hacker News post is live
- [ ] 42 Berlin post is live
- [ ] GitHub Pages website is live
- [ ] 50+ GitHub stars within 1 week
- [ ] 10+ users report trying it

---

### Phase 6: Connectors (Month 3)
**Goal:** Make it useful for real workflows.
**Deliverable:** 3 working connectors (GitHub, Slack, file import).

**Tasks:**
1. GitHub connector: webhook for commit messages
2. Slack connector: bot command `@mnemosyne remember this`
3. File import: bulk import from Markdown files
4. Add connector framework (plugin interface)
5. Document each connector
6. Git commit: `feat: add GitHub, Slack, and file import connectors`

**Session needed:** Builder session (connectors)
**Review needed:** Architect session reviews PR
**Test needed:** Test session tests each connector

**Exit criteria:**
- [ ] GitHub webhook stores commit messages as memories
- [ ] Slack bot responds to commands
- [ ] File import bulk loads markdown files
- [ ] Connector tests pass
- [ ] Documentation for each connector exists

---

### Phase 7: Advanced Features (Month 4-6)
**Goal:** Add features that make it sticky.
**Deliverable:** Emotional salience v2, graph visualization, web dashboard.

**Tasks (pick 2-3 per month):**
1. Emotional salience v2 (auto-detect emphasis markers)
2. Graph visualization (D3.js, static HTML)
3. Simple web dashboard (search, browse, add memory)
4. Prospective memory v2 (recurring cron expressions)
5. Memory versioning (Git-style, simple)
6. Team namespace (shared vault, not multi-tenant)

**Session needed:** Builder session (one feature per session)
**Review needed:** Architect session reviews each PR
**Test needed:** Test session tests each feature

---

## 5. BUILD SESSION PROMPTS

Each builder session will receive a prompt with:

### 5.1 Prompt Template

```
# BUILD SESSION: [Phase Name] - [Task Name]

## Context
You are a builder session working on the Mnemosyne project. The architect session
has planned this work. You have a fresh context window. Focus on implementation only.

## Project Overview
Mnemosyne is a local-first memory system for AI agents. It stores memories as
Markdown files, uses PostgreSQL + pgvector for search, and exposes an MCP server.
Repository: github.com/M4F-S/mo-graphify-obsidian-memory

## Phase Context
[Phase number and description from master plan]

## Specific Task
[Detailed task description]

## Files to Work With
[List of files to create/modify]

## Constraints
- Do NOT modify files outside the scope of this task
- Do NOT add features not specified in this task
- All code must have docstrings and type hints
- All code must pass `flake8` and `mypy`
- Add tests for all new functionality
- Git commit after each logical unit of work

## Definition of Done
[Exit criteria from master plan]

## Handoff
When done, create a HANDOFF.md file with:
1. What was built
2. Files modified
3. Decisions made
4. Issues found
5. Next steps
```

### 5.2 Phase 0 Builder Prompt (Corrected)

**This is the prompt to spawn the Phase 0 builder session with. It includes all fixes from the pre-build review.**

See file: `docs/build-prompts/prompt-phase-0-foundation.md`

---

## 6. REVIEW AND AUDIT PROCESS

### 6.1 Architect Review Checklist

For every PR from a builder session, the architect (this session) checks:

| Check | Criteria | Pass/Fail |
|-------|----------|-----------|
| **Scope** | Only changes specified in the task | ☐ |
| **Quality** | Docstrings, type hints, error handling | ☐ |
| **Tests** | New tests added, all tests pass | ☐ |
| **Style** | Passes `flake8` and `black` | ☐ |
| **Docs** | README/docs updated if needed | ☐ |
| **Git** | Clean commit history, proper messages | ☐ |
| **Security** | No secrets, no injection vulnerabilities | ☐ |
| **Backward Compat** | No breaking changes without migration | ☐ |

### 6.2 Audit Session Triggers

An audit session is spawned when:
- Before any release (tag creation)
- After 3 consecutive builder sessions (cumulative review)
- When a security-related change is made
- When a new feature touches the core architecture

**Audit session prompt:**
```
# AUDIT SESSION: Security and Quality Review

## Task
Review the codebase for security issues, code quality, and architecture consistency.

## Scope
Review all files modified in the last 3 PRs:
- [List files]

## Checks
1. Security: SQL injection, path traversal, injection attacks, secrets in code
2. Quality: Test coverage, error handling, logging, type safety
3. Architecture: Consistency with master plan, no scope creep
4. Performance: N+1 queries, memory leaks, slow paths
5. Documentation: README accuracy, API docs completeness

## Output
Create `AUDIT_REPORT.md` with:
- Findings (critical, high, medium, low)
- Recommendations
- Risk assessment
```

---

## 7. COMMUNICATION PROTOCOL

### 7.1 Between User and Architect (This Session)

The user communicates with the architect session for:
- Strategic decisions
- Feature prioritization
- Funding/timeline discussions
- Final approval of PRs
- Escalation of issues

### 7.2 Between Architect and Builder Sessions

The architect spawns builder sessions with:
- Detailed prompts (see Section 5)
- Clear scope and constraints
- Definition of done
- Handoff template

Builder sessions report back with:
- HANDOFF.md file
- PR link
- Test results
- Issues encountered

### 7.3 Using Memory Skill for Persistence

After each session, save key decisions to the vault:

```python
from mnemosyne import UnifiedMemorySystem
mem = UnifiedMemorySystem()

# Save architectural decision
mem.remember(
    title="Decision: [Topic]",
    content="[Detailed decision with rationale and alternatives considered]",
    tags=["decision", "architecture", "phase-N"],
    salience=0.9
)

# Save session summary
mem.remember(
    title="Session Summary: [Phase] - [Date]",
    content="[What was done, what was learned, what was decided]",
    tags=["session-log", "phase-N"],
    salience=0.7
)

# Save issue found
mem.remember(
    title="Issue: [Description]",
    content="[Detailed issue, impact, workaround, fix plan]",
    tags=["bug", "phase-N", "priority-high"],
    salience=0.8
)
```

---

## 8. RISK MANAGEMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Context compression loses decisions | High | High | Save all decisions to vault |
| Builder session produces poor code | Medium | High | Architect review + audit session |
| User has less time than planned | High | Medium | Phase 0-2 are minimal viable |
| Competitor releases similar feature | Medium | Medium | Speed > perfection, ship fast |
| PostgreSQL dependency scares users | Medium | High | SQLite fallback (Phase 1) |
| MCP spec changes again | Low | Medium | Abstract transport layer |
| VPS costs too much | Low | Low | Hetzner CX11 is €4/month |
| No users after launch | Medium | High | 42 Berlin network is guaranteed audience |

---

## 9. SUCCESS METRICS

| Phase | Stars | Users | Tests | Coverage | Days |
|-------|-------|-------|-------|----------|------|
| Phase 0 (Foundation) | 0 | 0 | 10+ | 50% | 7-14 |
| Phase 1 (SQLite) | 0 | 0 | 20+ | 60% | 7 |
| Phase 2 (MCP v2) | 0 | 0 | 30+ | 70% | 7 |
| Phase 3 (CLI) | 0 | 0 | 40+ | 75% | 7 |
| Phase 4 (VPS) | 0 | 0 | 50+ | 80% | 7 |
| Phase 5 (Launch) | 50+ | 10+ | 50+ | 80% | 7 |
| Phase 6 (Connectors) | 100+ | 20+ | 60+ | 80% | 14 |
| Phase 7 (Advanced) | 300+ | 50+ | 80+ | 85% | 30 |

---

## 10. APPENDICES

### A.1 Git Commands Reference

```bash
# Daily workflow
git checkout develop
git pull origin develop
git checkout -b feature/phase-0-restructure
# ... work ...
git add .
git commit -m "feat: add pyproject.toml and requirements.txt"
git push origin feature/phase-0-restructure
# Create PR on GitHub, merge to develop

# Release workflow
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0
# Update version, changelog
git commit -m "chore: bump version to 1.0.0"
git push origin release/v1.0.0
# Create PR to main, merge, tag
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### A.2 Session Spawn Commands

```
# Spawn builder session
Agent: description="Builder: Phase 0 restructure", prompt="[Prompt from Section 5]"

# Spawn test session
Agent: description="Test: Phase 0 tests", prompt="[Test prompt]"

# Spawn audit session
Agent: description="Audit: Security review", prompt="[Audit prompt]"
```

### A.3 Memory Vault Decision Log

All decisions are saved to:
```
~/Documents/Kimi/Workspaces/Mnemosyne/obsidian-vault/
├── decisions/        # Architectural decisions
├── sessions/         # Session summaries
├── issues/           # Bugs and issues
├── reviews/          # Pre-build reviews and audits
├── roadmap/          # Roadmap versions
└── *.md             # Regular notes
```

Sync protocol: Copy `decisions/` and `sessions/` to `docs/` in repo after each phase.

---

*Document: Mnemosyne Project Master Plan v1.1*
*Updated by: Architect Session*
*Date: July 7, 2026*
*Status: Planning Complete — Ready for Phase 0*
*Next Action: Spawn Builder Session for Phase 0 (Restructure Repo)*
*Changes from v1.0:*
* - Added 8 code bugs found in pre-build review*
* - Added 12 planning gaps and their fixes*
* - Specified `pyproject.toml` as ONLY packaging file*
* - Specified Apache 2.0 license*
* - Added Dockerfile to Phase 0*
* - Specified Python 3.9-3.12 test matrix*
* - Added vault-to-GitHub sync protocol*
* - Added builder failure protocol*
* - Created `develop` branch*
