# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
