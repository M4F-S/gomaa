---
name: mo-graphify-obsidian-memory
description: Graph-based knowledge memory system using Obsidian markdown vault files with wiki-links, hierarchical wing/room scoping, verbatim session capture, temporal decay, and timeline logging. Triggered by graphify my knowledge, obsidian memory, unified memory, save to memory, remember this, knowledge graph, memory vault, prospective memory, memory search, consolidate memory, semantic search, graph traversal, salience scoring, admission control, MCP server, memory timeline, memory history.
---

# mo-Graphify + Obsidian Memory v3.0

Production-grade unified memory for AI agents. Remember conversations, search by meaning and scope, schedule future reminders, inspect version history, and protect against poisoned data. All memories are plain `.md` files you can open in Obsidian or any text editor.

## What It Does

| Feature | What It Means |
|---------|-------------|
| **Hierarchical Scoping** | Organize memories by **Wing** (project/domain) and **Room** (topic). Query scoped domains without cross-topic pollution. |
| **Verbatim Session Ingestion** | Store transcripts verbatim without lossy summarization. Auto-chunked and indexed for high-fidelity retrieval. |
| **Temporal Decay** | Active memories persist; unaccessed memories gracefully decay over time and archive safely. |
| **Timeline Activity Log** | Complete chronological audit of all memory actions (`remember`, `recall`, `remind`, `consolidate`). |
| **Memory Versioning** | Full snapshot history preserved before updates. Inspect past versions with `memory_history`. |
| **Markdown Vault** | Plain `.md` files with YAML frontmatter. Human-readable, Git-diffable, portable. |
| **Semantic Search** | Vector similarity powered by `pgvector` with cosine similarity. |
| **Graph Memory** | Notes link via `[[wiki-links]]`. Traverse relationships 2+ hops deep. |
| **Security Gate** | Injection detection (MINJA/ADAM guard), near-duplicate check, contradiction flagging. |
| **Salience Scoring** | Important memories persist longer. Auto-calculated from emphasis markers + type. |
| **Prospective Memory** | "Remember to check this in 3 days" — scheduled reminders and recurring tasks. |
| **Sleep Consolidation** | Nightly maintenance: decay stale items, archive low salience, fix broken links. |
| **MCP Server** | Compatible with Hermes, Claude Code, Cursor, and standard Model Context Protocol clients. |

## MCP Tools (v3.0)

1. `memory_remember`: Save a memory note with title, content, tags, salience, `wing`, and `room`.
2. `memory_recall`: Search memories via `hybrid`, `semantic`, `keyword`, or `graph` modes with optional `scope` (`wing`, `room`).
3. `memory_ingest_session`: Auto-chunk and save entire conversation transcripts verbatim.
4. `memory_timeline`: Retrieve the recent log of memory operations.
5. `memory_history`: View prior version snapshots of an edited note.
6. `memory_remind_me`: Schedule future reminders (once or daily/weekly/monthly).
7. `memory_audit`: System health, version info, active wings, and storage metrics.
