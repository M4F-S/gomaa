# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.6] - 2026-11-20

### Fixed
- **Recall could inject stale snapshots as current fact.** `search_semantic`/`search_keyword` did
  not return `created_at`/`updated_at`, so the recency tie-break in the recall service never fired.
  Both now select and return the timestamps.
- `rank_rows` skips notes with `superseded_by` set (history must not be injected), and penalises
  perishable notes (`live-state`, `snapshot`, `status` tags or "live state" in the title) by age —
  up to −4 points after 20 days — so a current note wins over an old snapshot.
- `format_block` labels perishable notes with `[as of YYYY-MM-DD]` so the model can discount age.

### Added
- Three regression tests: superseded notes excluded, old snapshot loses to a fresh note, and the
  `as of` label is rendered.

## [Unreleased]

### Added
- **Read-only recall service (`gomaa.recall_service`)**: a small HTTP endpoint (`GET /health`,
  `POST /recall`) over the existing store, for callers that cannot import the package — an agent
  runtime without psycopg2/numpy/sentence-transformers, or a non-Python agent. Hybrid
  semantic+keyword retrieval fused by RRF, structural re-ranking, a hard character budget, and an
  optional per-query JSONL log of injected titles (never content). It deliberately bypasses
  `UnifiedMemorySystem.recall()`, which updates `access_count` on every returned row and would let a
  per-turn caller distort ACTR ranking and decay. Shared memory is off by default: measured on a
  live 260-note store, shared fleet policies outranked the specific project note (hit@3 2/10 with
  shared rows, 5/10 without).
- **`scripts/benchmark_recall.py`**: mechanical recall scoring (`hit@1`, `hit@k`, p50/p95) against a
  running service or the store, from a JSON/JSONL question file whose questions must paraphrase a
  note rather than repeat its title.
- **`docs/recall-service.md`**: the API, the four rules above with their measurements, and the
  client-side pattern for a per-turn memory provider (background query + cached block, dedupe of
  already-injected titles, bounded block size).
- **`tests/test_recall_service.py`**: 12 tests covering RRF fusion, room/scope penalties and boosts,
  recency as a tie-break only, budget truncation (including a budget smaller than one bullet), the
  service's read-only path, and the HTTP handler's `/health` and `/recall` endpoints.

## [4.0.5] - 2026-11-20

### Fixed
- **Re-landed the 4.0.4 hardening that `80003cf` had reverted on `main`.** Production already ran
  these changes; the default branch did not, so rebuilding from `main` would have reintroduced:
  - `create_store()` silently falling back to a private SQLite file when a configured Postgres DSN
    is unreachable (split-brain). It now raises unless `MEMORY_ALLOW_SQLITE_FALLBACK=1` is set;
    explicit SQLite paths and `MEMORY_REQUIRE_POSTGRES` behave as before.
  - dashboard token comparison via `==` instead of `hmac.compare_digest`, missing `Vary: Origin`,
    and no refusal to bind a non-loopback address without `GOMAA_DASHBOARD_TOKEN`.
  - REM link discovery seeded from the letter "a" instead of `list_notes()`.

### Changed
- CI pins the runner image per Python version (3.9 is not installable on ubuntu-26.04), runs the
  real Postgres contract tests instead of a SQLite test mislabelled as Postgres, and is ruff-clean.
- `scripts/test.sh`: chunked test runner for hosts where the full suite is SIGKILLed.
- Restored `tests/test_hardening_404.py` and `tests/test_retrieval_golden.py`, deleted by the revert.

## [4.0.4] - 2026-11-01

### Added
- Fail-closed `create_store()` on an unreachable configured Postgres DSN (opt-out
  `MEMORY_ALLOW_SQLITE_FALLBACK=1`); dashboard constant-time token comparison, `Vary: Origin`, and
  refusal to bind non-loopback without a token; REM seeding from `list_notes()`; hardening and
  retrieval golden tests.
- Shipped as tag `v4.0.4` (32d0e2c) and deployed to the fleet, but never merged to `main`; the
  changes were reverted there in `80003cf` and are restored in 4.0.5.

## [4.0.3] - 2026-11-01

### Fixed
- `forget` removes identical duplicate copies and proves the row lock.

## [4.0.0] - 2026-10-14

### Added
- **4-Quadrant Cognitive Architecture**: Dedicated stores for Episodic (`episodic_events`), Semantic (`notes` + `links`), Procedural (`procedural_playbooks` with Laplace utility), and Working Memory (`working_memory` bounded by Miller's Law $7 \pm 2$).
- **HippoRAG 2 Associative Memory Walker**: Single-step multi-hop retrieval using Personalized PageRank (`associative_ppr`) over bi-directional graph links with ACT-R base-level activation.
- **3-Phase Biological Sleep Consolidation (`gomaa sleep`)**: Slow-Wave Sleep crystallization + REM swarm skill sharing & latent link discovery + Assumption-based Truth Maintenance (ATMS) synaptic homeostasis.
- **Universal Cloud & Local Vault Backup Engine (`gomaa backup`, `gomaa restore`, `gomaa sync-folder`)**: Native support for creating timestamped compressed archives (.tar.gz, .zip) of vaults and databases, safe extraction with Tar-Slip/Zip-Slip protection, and folder sync with Google Drive for Desktop, Dropbox, and iCloud Drive.
- **Google Drive Conflict Branch Preservation**: `.conflict-TIMESTAMP.md` conflict note preservation on bidirectional Google Drive synchronization.
- **Expanded Test Suite**: 126 automated tests passing across 33 test modules with 100% test pass rate.

## [3.5.0] - 2026-08-29

### Added
- **Gomaa Autonomous Memory Platform (v3.5.0)**: Renamed and consolidated engine to `gomaa` with zero-duplication backward compatibility shims in `gomaa/` issuing deprecation warnings.
- **Embedded Web Knowledge Graph Dashboard (`gomaa dashboard`)**: Zero-dependency standard library HTTP dashboard visualizing real-time knowledge graphs, 5-layer cognitive memory distributions, and live search testing sandbox.
- **Token-Budgeted Prompt Context Assembler (`memory_assemble_context`)**: Retrieves, ranks, and packs high-salience memories into exact LLM token limits wrapped in escaped XML context blocks (`<recalled_memory_context>`).
- **5 Cognitive Memory Layers**: Scientific memory taxonomy (Episodic, Semantic, Procedural, Social, Preferential).
- **Simplified 2-Mode Installation**: Cleanly separated into Option 1 (Full Production Fleet with PostgreSQL + pgvector) and Option 2 (Lightweight Standalone with SQLite WAL & Markdown Vault).
- **CLI Connection Flexibility**: `--vault-path`, `--dsn`, and `--shared-dsn` flags now supported both before and after subcommands.

### Fixed & Hardened
- **Dashboard Stored XSS Hardening**: Added `escapeHtml()` sanitization across note titles, wings, rooms, and timeline events in `index.html`.
- **Dockerfile & Compose Defaults**: Standardized package copying (`gomaa/`) and defaulted DSN interpolation to `${POSTGRES_PASSWORD:-gomaa_secure_password}` for out-of-the-box local execution.
- **Scrubbed Password Literals in Documentation**: Sanitized all documentation examples to use generic environment variable templates.
- **Automated Test Coverage**: Expanded automated test suite to 94 tests across 28 test modules with 100% pass rate.

## [3.4.0] - 2026-08-24

### Added
- **Asynchronous Google Drive Synchronization (`gomaa.sync.gdrive`)**: Local-first sync engine supporting Service Account and OAuth2 credentials with bidirectional MD5-verified push/pull and automatic conflict branch preservation (`.conflict-TIMESTAMP.md`).
- **CLI Sync Command (`gomaa sync-gdrive`)**: Run one-off or continuous background daemon synchronization (`--daemon --interval 60`).
- **High-Recall HNSW Vector Indexing**: Upgraded PostgreSQL `pgvector` indexing to `HNSW (vector_cosine_ops) WITH (m=16, ef_construction=64)` with automated fallback to IVFFlat for legacy versions.
- **FastEmbed ONNX Runtime Support**: Optional lightweight ONNX embedding engine (~30MB RAM footprint, zero PyTorch dependency).
- **Expanded Credential Screening**: `_sanitize_for_shared()` strengthened with regex guards for Anthropic (`sk-ant-`), Google Gemini (`AIza...`), HuggingFace (`hf_...`), OpenAI project keys (`sk-proj-...`), Slack, AWS, and GitHub PATs.

### Fixed & Hardened
- **Transactional Dual-Write Ordering**: `remember()` commits to the local Markdown vault atomically first, rolling back and removing newly created notes if database upsert fails.
- **MCP Error Resilience**: `MCPServer._handle` rejects non-dict payloads with code `-32600` and extracts tool parameters defensively to eliminate unhandled `KeyError` crashes.
- **Broken Pipe Protection**: MCP stdio stdout flushes wrapped with `(BrokenPipeError, IOError)` handlers.
- **XML Context Injection Guard**: Both opening `<recalled_memory_context` and closing `</recalled_memory_context>` tags escaped during memory recall.
- **Admission Control Logging**: Closed silent fail-open `except Exception: pass` gaps with structured warning logs.

## [3.0.0] - 2026-08-22

### Added
- **Hierarchical Scoping (Wing & Room taxonomy)**: Inspired by MemPalace, added `wing` (project/domain) and `room` (topic) columns to `notes` table with composite indexing. `memory_remember` and `memory_recall` now support granular scoping to prevent cross-domain context contamination.
- **Verbatim Session Capture**: Added `memory_ingest_session` MCP tool for automatic verbatim transcript chunking and indexing without lossy summarization.
- **Temporal Decay Engine**: Added `last_accessed_at` tracking on retrieval. Nightly consolidation applies exponential decay `salience * (0.95 ^ days)` and automatically archives memories below threshold (0.05).
- **Timeline Activity Logging**: Added `timeline` table and `memory_timeline` MCP tool to record all memory operations (`remember`, `recall`, `remind`, `consolidate`, `ingest_session`).
- **Memory Versioning**: Added `note_versions` table and `memory_history` MCP tool. Updates archive previous snapshots before overwriting, preventing silent loss.
- **Full JSON-RPC MCP Compliance**: Implemented `ping` keepalive handler and strict `serverInfo` metadata block (version `3.0.0`).
- **Fleet Database Isolation**: Production deployment supporting isolated per-agent PostgreSQL vector databases (e.g. orchestrator, analyst, executor, operations, security).

### Changed
- `memory_recall` updated to support `scope` parameter (`wing`, `room`) across semantic, keyword, and hybrid RRF search modes.
- `serverInfo` in MCP `initialize` updated to report `{"name": "gomaa", "version": "3.0.0"}`.
- Refactored `PgVectorStore` to automatically manage schema migrations and table indexes.

## [2.0.0] - 2026-08-22
### Added
- PostgreSQL + pgvector vector store backend.
- Hybrid search merging semantic similarity, full-text tsvector rank, and salience scoring via Reciprocal Rank Fusion (RRF).
- Graph search traversing wiki-link relationships using recursive CTEs.


## [3.2.0] - 2026-08-24
### Added
- **Centralized Embedding Microservice (`gomaa.embed_service`):** High-efficiency FastAPI microservice running ONNX/SentenceTransformers in ~75MB RAM.
- **Circuit Breaker & Zero-RAM Fallback:** Embedder client includes connection reuse with `httpx`, circuit breaker, and keyword-search graceful degradation.
- **Thread-Safe Self-Healing Database Pooling:** `PgVectorStore` uses `ThreadedConnectionPool` with liveness checks and auto-reconnect on dead sockets.
- **Cross-Agent Shared Memory Layer (`shared_db`):** Multi-tenant fleet memory with `memory_publish_shared`, regex credential sanitization, and fail-soft recall.
- **Real-Time & Set-Based Wikilink Graph Engine:** O(1) reverse link resolution on note creation and sub-second set-based SQL graph reconciliation.

## [3.3.0] - 2026-08-24
### Security & Resilience Patch
- **Strict Path Traversal Immunity:** Dual-resolved canonical path verification preventing directory traversal across wings, rooms, and titles.
- **Atomic Sibling File Writes:** Atomic `.tmp` to destination writes with `EXDEV` cross-device fallback handling for Docker volume mounts.
- **Code-Safe Injection Neutralizer:** Neutralizes prompt injection control tokens (`<|im_start|>`, `[INST]`) in prose while preserving code blocks.
- **Structured XML Context Enclosure:** Recalled memories wrapped in `<recalled_memory_context>` tags with closing tag escaping.
- **Recursive Graph Cycle Prevention:** Added `ARRAY[]` path accumulation and cycle termination to PostgreSQL recursive CTEs.
- **WebSearch FTS (`websearch_to_tsquery`):** Native phrase quotes and `-exclusions` with unescaped punctuation safety.
- **Selective Access Touch (Decay Feedback Fix):** Mode-specific relevance thresholds preventing low-confidence matches from resetting Ebbinghaus decay.
- **Linear Sliding-Window Chunking:** Turns $>1,500$ chars chunked into overlapping linear sequences, ensuring 100% vector indexing without Obsidian graph mesh clutter.
