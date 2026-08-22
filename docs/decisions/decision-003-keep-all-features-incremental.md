---
title: "Decision: Keep All Features, Build Incrementally"
date: 2026-07-07
tags: [decision, architecture, features, incremental]
type: decision
salience: 0.9
links: []
---

# Decision: Keep All Features, Build Incrementally

## Context

The user stated: "I want to keep all but we can start small and add features along the way, as much as we can code."

The audit recommended cutting 70% of features. The user rejected this and wants to keep the full vision but build incrementally.

## Decision

We ACCEPT the user's decision to keep all features. The implementation strategy is:

1. **Core features are already built** (15 features in `mo_graphify_memory.py`):
   - Remember, recall, semantic search, keyword search, graph search, hybrid RRF
   - Markdown vault, YAML frontmatter, wiki-links
   - Admission control, salience scoring, prospective memory, consolidation
   - MCP server (v1, JSON-RPC with initialize handshake), backward compatibility

2. **Phase 0-2 makes the core shippable** (restructure, SQLite, MCP v2)

3. **Later phases add new features** (connectors, viz, dashboard, etc.)

4. **The architecture is designed to accommodate all features** without rewriting

## Feature Inventory

### Already Built (in `mo_graphify_memory.py`)

| Feature | Status | File | Notes |
|---------|--------|------|-------|
| Remember/Recall | ✅ | `mo_graphify_memory.py` | |
| Semantic Search | ✅ | `mo_graphify_memory.py` | |
| Keyword Search | ✅ | `mo_graphify_memory.py` | |
| Graph Search | ✅ | `mo_graphify_memory.py` | |
| Hybrid RRF | ✅ | `mo_graphify_memory.py` | |
| Markdown Vault | ✅ | `mo_graphify_memory.py` | |
| YAML Frontmatter | ✅ | `mo_graphify_memory.py` | |
| Wiki-Links | ✅ | `mo_graphify_memory.py` | |
| Admission Control | ✅ | `mo_graphify_memory.py` | |
| Salience Scoring | ✅ | `mo_graphify_memory.py` | |
| Prospective Memory | ✅ | `mo_graphify_memory.py` | |
| Consolidation | ✅ | `mo_graphify_memory.py` | Partial (archive + relink only) |
| MCP Server v1 | ✅ | `mo_graphify_memory.py` | JSON-RPC with initialize handshake |
| Backward Compat | ✅ | `mo_graphify_memory.py` | v1.0 API functions |
| 3-Tier Embedder | ✅ | `mo_graphify_memory.py` | sentence-transformers → Ollama → hash |

### To Be Added (phased)

| Feature | Phase | Effort | Status |
|---------|-------|--------|--------|
| SQLite Fallback | Phase 1 | 3 days | ❌ |
| MCP v2 (stateless, 2026-07-28) | Phase 2 | 3 days | ❌ |
| CLI Tool | Phase 3 | 3 days | ❌ |
| VPS Deploy | Phase 4 | 3 days | ❌ |
| GitHub Connector | Phase 6 | 3 days | ❌ |
| Slack Connector | Phase 6 | 3 days | ❌ |
| File Import | Phase 6 | 2 days | ❌ |
| Graph Visualization | Phase 7 | 3 days | ❌ |
| Web Dashboard | Phase 7 | 1 week | ❌ |
| Emotional Salience v2 | Phase 7 | 2 days | ❌ |
| Memory Versioning | Phase 7 | 1 week | ❌ |
| Plugin System | Phase 7 | 2 weeks | ❌ |
| Browser Extension | Phase 7 | 2 weeks | ❌ |
| VS Code Extension | Phase 7 | 2 weeks | ❌ |
| Mobile App | Phase 7 | 1 month | ❌ |
| Plugin Marketplace | Year 2 | 3 months | ❌ |
| SOC 2 | Year 2 | 3 months | ❌ |
| EU AI Act | Year 2 | 3 months | ❌ |
| TEE Integration | Year 2 | 2 months | ❌ |
| Differential Privacy | Year 2 | 2 months | ❌ |

## Correction from Pre-Build Review

**Previous inconsistency:** Decision originally marked "MCP Server" as ✅ (done) without distinguishing v1 vs v2. This was ambiguous.

**Correction:**
- MCP Server v1 (JSON-RPC with `initialize` handshake) — ✅ Already built
- MCP Server v2 (stateless, 2026-07-28 spec, no handshake) — ❌ Phase 2

The v1 server works today. The v2 update is a new feature for Phase 2.

## Rationale

The user is the decision-maker. They want to keep the full vision. Our job is to make it implementable by breaking it into phases. The core is already built - we're packaging and extending, not rewriting.

## Consequences

- Positive: Full vision preserved, each phase adds value
- Negative: Longer timeline, more complexity, risk of never finishing
- Mitigation: Phase 0-2 is the MVP - if we stop there, we still have a working product

## Status: ACCEPTED

## Date: 2026-07-07 (updated from 2026-07-06)
## Version: 1.1
