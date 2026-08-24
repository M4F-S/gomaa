# Mnemosyne Handover Dossier 🧠

**Generated:** 2026-08-24  
**Repository:** [https://github.com/M4F-S/mnemosyne](https://github.com/M4F-S/mnemosyne)  
**Package:** `mnemosyne-memory` (v3.4.0)  
**Live Production Host:** VPS `187.124.2.26`  

---

## 📌 Executive Summary

**Mnemosyne** is an MCP-native, hierarchical long-term memory engine for autonomous AI agents. It unites **human-readable Obsidian Markdown Vaults** with **PostgreSQL + pgvector** (or zero-dependency **SQLite**), providing agents with persistent knowledge, semantic search, knowledge graphs, and temporal decay.

### Core Differentiators
1. **Model Context Protocol (MCP) First:** Native stdio JSON-RPC server with zero stdout pollution, plug-and-play with Claude Desktop, Cursor, OpenClaw, Hermes, and OpenHands.
2. **Hybrid RRF Search:** Fuses dense semantic vector embeddings (`all-MiniLM-L6-v2`), PostgreSQL full-text search (`tsvector`), recursive wikilink graph traversal, and salience scoring into a unified Reciprocal Rank Fusion metric.
3. **Hierarchical Scoping (`wing` & `room`):** Isolates project, client, or domain knowledge to prevent context pollution across fleets of agents.
4. **Ebbinghaus Temporal Decay with Pinned Immunity:** Slowly decays idle memories over time while permanently preserving mission-critical notes marked `pinned=True`.
5. **Zero-Setup SQLite Parity:** Standalone 100% feature-complete fallback when PostgreSQL is unavailable.

---

## 📂 Dossier Contents

| File | Purpose |
|---|---|
| [`01_FLEET_ARCHITECTURE_AND_PORTS.md`](01_FLEET_ARCHITECTURE_AND_PORTS.md) | Full VPS infrastructure, container inventory, internal networks, ports, and DSNs |
| [`02_TECHNICAL_SPECIFICATION_V3.1.md`](02_TECHNICAL_SPECIFICATION_V3.1.md) | Database schemas, RRF ranking math, Ebbinghaus decay formulas, and admission control |
| [`03_AGENT_INTEGRATIONS_CATALOG.md`](03_AGENT_INTEGRATIONS_CATALOG.md) | Configuration guides for OpenClaw, Hermes, Claude, Cursor, OpenManus, CrewAI, LangChain |
| [`04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md`](04_GITHUB_STARS_AND_DISTRIBUTION_PLAN.md) | Social launch kit, HN Show HN copy, Twitter threads, Reddit strategy, Awesome-MCP PR |
| [`05_OPERATIONS_AND_RUNBOOK.md`](05_OPERATIONS_AND_RUNBOOK.md) | Maintenance scripts, test commands, backup procedures, and troubleshooting guide |
| [`06_FUTURE_ROADMAP.md`](06_FUTURE_ROADMAP.md) | Upcoming features: SSE/HTTP transport, web UI visualizer, multi-tenant auth |
