# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.5.0] - 2026-08-29

### Added
- **Gomaa Autonomous Memory Platform (v3.5.0)**: Renamed and consolidated engine to `gomaa` with zero-duplication backward compatibility shims in `mnemosyne/` issuing deprecation warnings.
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
- **Asynchronous Google Drive Synchronization (`mnemosyne.sync.gdrive`)**: Local-first sync engine supporting Service Account and OAuth2 credentials with bidirectional MD5-verified push/pull and automatic conflict branch preservation (`.conflict-TIMESTAMP.md`).
- **CLI Sync Command (`mnemosyne sync-gdrive`)**: Run one-off or continuous background daemon synchronization (`--daemon --interval 60`).
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
- **Fleet Database Isolation**: Production deployment supporting isolated per-agent PostgreSQL vector databases (`toy_db`, `old_db`, `pencil_db`, `trader_db`, `candy_db`).

### Changed
- `memory_recall` updated to support `scope` parameter (`wing`, `room`) across semantic, keyword, and hybrid RRF search modes.
- `serverInfo` in MCP `initialize` updated to report `{"name": "mnemosyne", "version": "3.0.0"}`.
- Refactored `PgVectorStore` to automatically manage schema migrations and table indexes.

## [2.0.0] - 2026-08-22
### Added
- PostgreSQL + pgvector vector store backend.
- Hybrid search merging semantic similarity, full-text tsvector rank, and salience scoring via Reciprocal Rank Fusion (RRF).
- Graph search traversing wiki-link relationships using recursive CTEs.


## [3.2.0] - 2026-08-24
### Added
- **Centralized Embedding Microservice (`mnemosyne.embed_service`):** High-efficiency FastAPI microservice running ONNX/SentenceTransformers in ~75MB RAM.
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
