# 🚀 Mnemosyne v3.0 — Open Source Launch Kit

---

## 1. 📰 Hacker News: "Show HN" Submission (2,292 chars / < 4,000 limit)

* **URL / Link:** `https://github.com/M4F-S/mnemosyne`
* **Title:** `Show HN: Mnemosyne – Local-first hierarchical memory engine for AI agents (MCP Native)`

### Text (Copy & Paste):

Hey HN,

I built Mnemosyne because my multi-agent fleet on a self-hosted VPS kept hitting the same wall: context window bloat and memory contamination.

When running autonomous agents (like Claude Code, Hermes, or Cursor-driven agents) for hours or days:
1. Short-term chat history balloons to 100k+ tokens, leading to HTTP 429 rate limits, slow latency, and massive API costs.
2. Flat vector databases cross-contaminate knowledge (e.g., backend DevOps credentials polluting frontend UI searches).
3. Most agent memory tools aggressively summarize past conversations with LLMs, losing exact code syntax, port numbers, and edge-case flags.
4. Stale memories from months ago rank equally with fresh context because older tools lack temporal forgetting curves.

Mnemosyne is a local-first memory operating system designed specifically for autonomous agent fleets.

Key Architecture Highlights:

• Hierarchical Scoping (Wings & Rooms): Organize memories by domain (Wing) and topic (Room). You can scope searches (e.g., wing="ecommerce") so a marketing agent never sees infrastructure credentials, eliminating cross-domain context pollution.

• Verbatim Session Mining: Ingest full conversation transcripts verbatim using local sentence-transformers embeddings ($0 API spend). Store exact code snippets, logs, and outputs with 100% fidelity.

• Triple Hybrid Retrieval (RRF): Merges dense vector embeddings (pgvector cosine distance), sparse full-text keyword search (PostgreSQL tsvector), and recursive CTE [[wiki-link]] graph traversal via Reciprocal Rank Fusion.

• Ebbinghaus Temporal Decay: Unaccessed memories decay via an exponential forgetting curve (salience * 0.95^days) and gracefully archive during nightly consolidation runs.

• Human-Readable Obsidian Vault: All memories are plain Markdown files with YAML frontmatter on your disk. You own the files and can open them directly in Obsidian.

• Native MCP Server: Exposes 7 standard JSON-RPC tools compatible out-of-the-box with Claude Desktop, Claude Code, Cursor IDE, OpenCode, and Hermes Agent.

The core engine is 100% open-source (Apache 2.0):
GitHub: https://github.com/M4F-S/mnemosyne

I would love feedback on the hierarchical scoping model and the RRF graph traversal. What memory patterns are you using in your agent stacks?

---

## 2. 🐦 X / Twitter Launch Thread

### Tweet 1 (The Hook)
AI agents get "dementia" or blow past 100k tokens after a few hours of autonomous work.

Summarizing loses exact code syntax. Flat vector DBs cause context contamination.

Today I’m open-sourcing Mnemosyne v3.0: A local-first, hierarchical memory OS for AI agents with $0 API spend. 🧠👇
https://github.com/M4F-S/mnemosyne

### Tweet 2 (Hierarchical Scoping)
Most memory DBs are flat. If your agent works on DevOps and E-commerce, the vector space gets polluted.

Mnemosyne introduces Wings (Projects) and Rooms (Topics).

An agent can scope its search: memory_recall("webhook secret", scope={"wing": "ecommerce"}) — 100% precision, zero noise.

### Tweet 3 (Verbatim Recall vs Lossy Summaries)
LLM-generated summaries are lossy. They drop exact flags, port numbers, and edge-case syntax.

Mnemosyne stores memories and session transcripts verbatim using local sentence-transformers + pgvector.

Retrieval merges Semantic Vector + Keyword tsvector + [[Wiki-link]] Graphs using Reciprocal Rank Fusion (RRF).

### Tweet 4 (Ebbinghaus Forgetting Curve)
Stale memories rot your index.

Mnemosyne implements dynamic temporal decay: memories you recall stay sharp; unaccessed memories decay exponentially and archive safely during nightly consolidation.

### Tweet 5 (MCP & 1-Click Install)
Native Model Context Protocol (MCP) support. Works instantly with:
• Claude Desktop
• Claude Code (claude mcp add)
• Cursor IDE
• Hermes Agent / LangChain

100% open-source (Apache 2.0). Plain Markdown vault you own.

⭐ Star on GitHub: https://github.com/M4F-S/mnemosyne
