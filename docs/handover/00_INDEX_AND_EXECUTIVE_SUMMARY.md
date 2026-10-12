# Gomaa Handover Dossier 🧠

**Generated:** 2026-10-12  
**Repository:** [https://github.com/M4F-S/gomaa](https://github.com/M4F-S/gomaa)  
**Package:** `gomaa` (v4.0.0 — "Gomaa Neo")  
**License:** Apache-2.0  
**Live Production Host:** VPS `${VPS_HOST}`  

---

## 📌 Executive Summary

**Gomaa v4.0.0 ("Gomaa Neo")** is an MCP-native, local-first hierarchical and neuro-inspired cognitive long-term memory engine for autonomous AI agents. It unites **human-readable Obsidian Markdown Vaults** with high-performance **PostgreSQL + pgvector (HNSW)** and zero-dependency **SQLite**, providing agents with a **4-Quadrant Cognitive Architecture** (Episodic, Semantic, Procedural, Working Memory), **HippoRAG 2 Personalized PageRank (PPR)** associative retrieval, **3-Phase Biological Sleep Consolidation** (SWS + REM + ATMS Homeostasis), hybrid Reciprocal Rank Fusion (RRF) search, Ebbinghaus temporal decay, cross-agent fleet sharing, and asynchronous Google Drive cloud synchronization.

### Core Differentiators (v4.0.0 — "Gomaa Neo")
1. **Model Context Protocol (MCP v2024-11-05) Native:** Full 13-tool stdio JSON-RPC server with zero stdout pollution and JSON-stringified argument coercion, plug-and-play with Claude Desktop, Cursor, OpenClaw, Hermes, and OpenManus.
2. **4-Quadrant Cognitive Architecture:** Explicit separation of Episodic (`episodic_events`), Semantic (`notes` + weighted `links`), Procedural (`procedural_playbooks` with Bayesian Laplace utility), and Working Memory (`working_memory` bounded by Miller's Law $7 \pm 2$).
3. **HippoRAG 2 Personalized PageRank (`associative_ppr`):** Single-step multi-hop associative retrieval via power-iteration PPR ($K=20, \alpha=0.15$) over bi-directional forward and backlink edges.
4. **3-Phase Biological Sleep Consolidation (`gomaa sleep`):** SWS high-surprise episode crystallization + procedural trajectory extraction, REM cross-agent playbook sharing + latent tag-bridge link discovery, and ATMS epistemic conflict resolution.
5. **High-Recall HNSW Vector Search:** Indexed with `pgvector HNSW (vector_cosine_ops, m=16, ef_construction=64)` for sub-millisecond similarity recall.
6. **Hybrid RRF + ACT-R Search with Cross-Store Ranking:** Fuses dense semantic vector embeddings, HippoRAG PPR, PostgreSQL full-text search (`tsvector`), recursive wikilink graph traversal, salience, and ACT-R base-level activation ($\ln(1 + \text{access\_count})$) across both private and shared fleet databases.
7. **Token-Budgeted Prompt Context Assembler (`memory_assemble_context`):** Packs top-salience memories into exact LLM token budgets wrapped in escaped XML context tags ready for system prompt injection.
8. **Cross-Agent Shared Knowledge (`shared_db`):** Multi-agent fleet intelligence layer with automated regex credential screening (Anthropic, Gemini, OpenAI, HuggingFace, AWS, GitHub).
9. **Embedded Web Knowledge Graph Dashboard (`gomaa dashboard`):** Zero-dependency standard library HTTP dashboard visualizing real-time memory graphs and cognitive layers.
10. **Asynchronous Google Drive Cloud Sync:** Local-first speed (<1ms) with background daemon/cron sync, MD5 hash verification, and sibling `.conflict-TIMESTAMP.md` conflict resolution.
11. **Zero-Setup SQLite Parity:** Standalone 100% feature-complete fallback when PostgreSQL is unavailable.

---

## 📂 Dossier Contents

| File | Purpose |
|---|---|
| [`01_FLEET_ARCHITECTURE_AND_PORTS.md`](01_FLEET_ARCHITECTURE_AND_PORTS.md) | Full VPS infrastructure, 5-container agent inventory, internal networks, ports, and DSNs |
| [`02_TECHNICAL_SPECIFICATION_V3.4.md`](02_TECHNICAL_SPECIFICATION_V3.4.md) | Database schemas, HNSW indexes, RRF ranking math, Ebbinghaus decay formulas, and MCP tool schemas |
| [`03_AGENT_INTEGRATIONS_CATALOG.md`](03_AGENT_INTEGRATIONS_CATALOG.md) | Configuration guides for Hermes, Claude Desktop, Cursor, OpenClaw, OpenManus, CrewAI, LangChain |
| [`04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md`](04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md) | Social launch kit, HN Show HN copy, Twitter threads, Reddit strategy, Awesome-MCP PR |
| [`05_OPERATIONS_AND_RUNBOOK.md`](05_OPERATIONS_AND_RUNBOOK.md) | Maintenance scripts, test commands, backup procedures, and troubleshooting guide |
| [`06_FUTURE_ROADMAP.md`](06_FUTURE_ROADMAP.md) | Upcoming features: SSE/HTTP transport, web UI visualizer, multi-tenant auth |
| [`07_GOMAA_V4_NEO_SPECIFICATION.md`](07_GOMAA_V4_NEO_SPECIFICATION.md) | Gomaa v4.0 ("Gomaa Neo") 4-Quadrant architecture, HippoRAG 2 PPR, and 3-phase Sleep Consolidation specification |

