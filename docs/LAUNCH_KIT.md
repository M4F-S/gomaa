# 🚀 Mnemosyne v3.0 — Open Source Launch Kit

This kit contains all the developer-focused launch materials, community posts, and MCP catalog PR templates to make **`M4F-S/mnemosyne`** viral on GitHub.

---

## 1. 📰 Hacker News: "Show HN" Submission

* **Title:** `Show HN: Mnemosyne – Local-first hierarchical memory engine for AI agents (MCP Native)`
* **URL / Link:** `https://github.com/M4F-S/mnemosyne`

### Post Body:

```markdown
Hey HN,

I built Mnemosyne because my multi-agent fleet on a self-hosted VPS kept hitting the same wall: context window bloat and memory contamination.

When running autonomous agents (like Claude Code, Hermes, or Cursor-driven agents) for hours or days:
1. Short-term chat history balloons to 100k+ tokens, leading to HTTP 429 rate limits, slow latency, and massive API costs.
2. Flat vector databases cross-contaminate knowledge (e.g. backend Python code snippets corrupt frontend React searches).
3. Most agent memory tools aggressively summarize past conversations with LLMs, losing exact code snippets, API keys, and nuance.
4. Old, stale memories from months ago rank equally with fresh context because older tools lack forgetting curves.

Mnemosyne is a local-first memory operating system designed to fix this:

• Hierarchical Scoping (Wings & Rooms): Memories are organized by domain (Wing) and topic (Room). You can scope searches so a marketing agent never sees infrastructure credentials.
• Verbatim Session Mining: Store conversations verbatim with local sentence-transformers embeddings ($0 API spend).
• Hybrid Graph + Vector RRF: Combines pgvector cosine similarity, PostgreSQL tsvector full-text search, and recursive CTE wiki-link graph traversal via Reciprocal Rank Fusion.
• Ebbinghaus Temporal Decay: Unaccessed memories decay via an exponential forgetting curve `salience * (0.95 ^ days)` and gracefully archive.
• Human Obsidian Vault: All memories are plain Markdown files with YAML frontmatter on your disk. You own the files.
• Native MCP Server: 7 standard JSON-RPC tools compatible out-of-the-box with Claude Desktop, Claude Code, Cursor, and Hermes.

The core engine is Apache 2.0 open-source:
GitHub: https://github.com/M4F-S/mnemosyne

I'd love feedback on the hierarchical scoping model and the RRF graph traversal. What memory patterns are you using in your agent stacks?
```

---

## 2. 🐦 X / Twitter Launch Thread

### Tweet 1 (The Hook & Video/GIF)
> AI agents get "dementia" or blow past 100k tokens after a few hours of autonomous work.
> 
> Summarizing loses exact code syntax. Flat vector DBs cause context contamination.
> 
> Today I’m open-sourcing **Mnemosyne v3.0**: A local-first, hierarchical memory OS for AI agents with $0 API spend. 🧠👇
> 
> [Attach Architecture Diagram or 15s Demo GIF]

### Tweet 2 (The Solution: Hierarchical Scoping)
> Most memory DBs are flat. If your agent works on DevOps and E-commerce, the vector space gets polluted.
> 
> Mnemosyne introduces **Wings** (Projects) and **Rooms** (Topics).
> 
> An agent can scope its search: `memory_recall("webhook secret", scope={"wing": "ecommerce"})` — 100% precision, zero noise.

### Tweet 3 (Verbatim Recall vs Lossy Summaries)
> LLM-generated summaries are lossy. They drop exact flags, port numbers, and edge-case syntax.
> 
> Mnemosyne stores memories and session transcripts **verbatim** using local `sentence-transformers` + `pgvector`.
> 
> Retrieval merges Semantic Vector + Keyword tsvector + [[Wiki-link]] Graphs using Reciprocal Rank Fusion (RRF).

### Tweet 4 (Ebbinghaus Forgetting Curve)
> Stale memories rot your index.
> 
> Mnemosyne implements dynamic temporal decay: memories you recall stay sharp; unaccessed memories decay exponentially and archive safely during nightly consolidation.

### Tweet 5 (MCP & 1-Click Install)
> Native Model Context Protocol (MCP) support. Works instantly with:
> • Claude Desktop
> • Claude Code (`claude mcp add`)
> • Cursor IDE
> • Hermes Agent / LangChain
> 
> 100% open-source (Apache 2.0). Plain Markdown vault you own.
> 
> ⭐ Star on GitHub: https://github.com/M4F-S/mnemosyne

---

## 3. 💬 Reddit Post (r/LocalLLaMA & r/MachineLearning)

* **Subreddits:** `r/LocalLLaMA`, `r/MachineLearning`, `r/ArtificialIntelligence`, `r/ClaudeAI`
* **Title:** `I built a local-first hierarchical memory system (pgvector + graph + MCP) for autonomous agents to fix context bloat`

### Post Body:

```markdown
Hi r/LocalLLaMA,

One of the biggest friction points when running local or API-driven agent fleets is managing long-term state without exploding the prompt context.

I built **Mnemosyne** to provide a production-grade, local-first alternative to cloud-dependent memory platforms.

### Key Highlights:
1. **Hierarchical Scoping (Wing/Room Taxonomy):** Prevents the classic problem of vector space contamination across multi-project workflows.
2. **Zero-API Cost:** Local embeddings via `sentence-transformers` and cosine indexing on `pgvector`.
3. **Triple Hybrid Retrieval (RRF):** Merges dense embeddings, sparse PostgreSQL `tsvector`, and graph relationships (recursive CTEs over `[[wiki-links]]`).
4. **Temporal Decay:** Ebbinghaus forgetting curve automatically decays salience on unreferenced notes and archives them to prevent memory rot.
5. **Human Readable:** Markdown files with YAML frontmatter sync with Obsidian.
6. **Native MCP Server:** 7 standard tools (`memory_remember`, `memory_recall`, `memory_ingest_session`, `memory_timeline`, `memory_history`, `memory_remind_me`, `memory_audit`).

Code & Docker Compose: https://github.com/M4F-S/mnemosyne

Looking for feedback on benchmark comparisons and potential integrations with local LLM harnesses (Ollama, vLLM, LMStudio)!
```

---

## 4. 🔌 Pull Request Template: `awesome-mcp-servers`

Submit this PR to:
1. **[punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)**
2. **[wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers)**

### PR Title:
`Add Mnemosyne - Local-first hierarchical memory engine for AI agents`

### Markdown Entry (to add under Knowledge & Memory section):

```markdown
- [Mnemosyne](https://github.com/M4F-S/mnemosyne) 🧠 - Production-grade, local-first memory operating system for AI agents featuring hierarchical wing/room scoping, verbatim transcript ingestion, hybrid graph + vector RRF search, and temporal decay.
```

---

## 5. 🔌 Submission to Official MCP Registry (`modelcontextprotocol/servers`)

### Server Metadata JSON:

```json
{
  "name": "mnemosyne",
  "description": "Local-first memory engine for AI agents with hierarchical scoping, verbatim ingestion, and pgvector hybrid search",
  "repository": "https://github.com/M4F-S/mnemosyne",
  "license": "Apache-2.0",
  "categories": ["memory", "knowledge-graph", "storage"],
  "transport": "stdio",
  "command": "python3",
  "args": ["-m", "mnemosyne.mcp_server"]
}
```
