# Mnemosyne Handover Dossier 🧠

**Generated:** 2026-08-25  
**Repository:** [https://github.com/M4F-S/mnemosyne](https://github.com/M4F-S/mnemosyne)  
**Package:** `mnemosyne-memory` (v3.4.0)  
**License:** Apache-2.0  
**Live Production Host:** VPS `<YOUR_VPS_IP>`  

---

## 📌 Executive Summary

**Mnemosyne** is an MCP-native, local-first hierarchical long-term memory engine for autonomous AI agents. It unites **human-readable Obsidian Markdown Vaults** with high-performance **PostgreSQL + pgvector (HNSW)** and zero-dependency **SQLite**, providing agents with persistent knowledge, hybrid Reciprocal Rank Fusion (RRF) search, wikilink knowledge graphs, Ebbinghaus temporal decay, cross-agent fleet sharing, and asynchronous Google Drive cloud synchronization.

### Core Differentiators (v3.4.0)
1. **Model Context Protocol (MCP v2024-11-05) Native:** Full 8-tool stdio JSON-RPC server with zero stdout pollution, plug-and-play with Claude Desktop, Cursor, OpenClaw, Hermes, and OpenHands.
2. **High-Recall HNSW Vector Search:** Indexed with `pgvector HNSW (vector_cosine_ops, m=16, ef_construction=64)` for sub-millisecond similarity recall.
3. **Hybrid RRF Search with Cross-Store Ranking:** Fuses dense semantic vector embeddings, PostgreSQL full-text search (`tsvector`), recursive wikilink graph traversal, and salience scoring into a unified Reciprocal Rank Fusion metric across both private and shared fleet databases.
4. **Cross-Agent Shared Knowledge (`shared_db`):** Multi-agent fleet intelligence layer with automated regex credential screening (Anthropic, Gemini, OpenAI, HuggingFace, AWS, GitHub).
5. **Asynchronous Google Drive Cloud Sync:** Local-first speed (<1ms) with background daemon/cron sync, MD5 hash verification, and sibling `.conflict-TIMESTAMP.md` conflict resolution.
6. **Hierarchical Scoping (`wing` & `room`):** Isolates project, client, or domain knowledge to prevent context pollution across fleets of agents.
7. **Ebbinghaus Temporal Decay with Pinned Immunity:** Slowly decays idle memories over time while permanently preserving mission-critical notes marked `pinned=True` or tagged `#pinned`.
8. **Turn-Aware Conversational Ingestor:** 1,500-character linear sliding-window chunking with 200-character overlap along turn boundaries, chained via `[[Wiki Links]]`.
9. **Zero-Setup SQLite Parity:** Standalone 100% feature-complete fallback when PostgreSQL is unavailable.

---

## 📂 Dossier Contents

| File | Purpose |
|---|---|
| [`01_FLEET_ARCHITECTURE_AND_PORTS.md`](01_FLEET_ARCHITECTURE_AND_PORTS.md) | Full VPS infrastructure, 5-container agent inventory, internal networks, ports, and DSNs |
| [`02_TECHNICAL_SPECIFICATION_V3.4.md`](02_TECHNICAL_SPECIFICATION_V3.4.md) | Database schemas, HNSW indexes, RRF ranking math, Ebbinghaus decay formulas, and 8 MCP tool schemas |
| [`03_AGENT_INTEGRATIONS_CATALOG.md`](03_AGENT_INTEGRATIONS_CATALOG.md) | Configuration guides for Hermes, Claude Desktop, Cursor, OpenClaw, OpenManus, CrewAI, LangChain |
| [`04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md`](04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md) | Social launch kit, HN Show HN copy, Twitter threads, Reddit strategy, Awesome-MCP PR |
| [`05_OPERATIONS_AND_RUNBOOK.md`](05_OPERATIONS_AND_RUNBOOK.md) | Maintenance scripts, test commands, backup procedures, and troubleshooting guide |
| [`06_FUTURE_ROADMAP.md`](06_FUTURE_ROADMAP.md) | Upcoming features: SSE/HTTP transport, web UI visualizer, multi-tenant auth |
