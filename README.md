<div align="center">

# 🧠 Mnemosyne v3.0

### The Local-First Memory Operating System for AI Agents
**Hierarchical Scoping • Verbatim Ingestion • Graph+Vector RRF • Zero Token Bloat • 100% Private**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.7+-green.svg)](https://github.com/pgvector/pgvector)
[![MCP Compatible](https://img.shields.io/badge/MCP-2024--11--05-orange.svg?logo=anthropic&logoColor=white)](https://modelcontextprotocol.io/)
[![Zero API Spend](https://img.shields.io/badge/Embeddings-$0%20Local-success.svg)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)

[Quickstart](#-30-second-quickstart) • [Architecture](#-architecture) • [MCP Setup (Claude / Cursor)](#-model-context-protocol-mcp-quickstarts) • [Comparison](#-feature-matrix--benchmarks) • [Documentation](docs/)

</div>

---

## ⚡ The Problem: Context Window Bloat & Memory Decay

As autonomous agents run for hours or weeks, standard conversation history creates massive operational bottlenecks:
1. **Context Window Explosions:** Chat histories balloon to hundreds of thousands of tokens, triggering rate limits (`HTTP 429`), massive API bills, and prompt latency.
2. **Context Contamination:** Flat vector databases mix unrelated domain data (e.g. coding snippets pollute marketing campaigns).
3. **Lossy Summaries:** Typical memory tools aggressively summarize past interactions, losing exact code snippets, API keys, and subtle syntax nuances.
4. **Memory Rot:** Irrelevant, months-old memories clutter search results because older tools lack temporal forgetting curves.

## 💎 The Solution: Mnemosyne v3.0

**Mnemosyne** is a production-grade, local-first memory operating system designed specifically for autonomous agent fleets. It combines **hierarchical project/topic taxonomy**, **verbatim session ingestion**, **hybrid graph + semantic vector retrieval**, and **human-readable Obsidian Markdown vaults**.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              AGENT / USER INTERACTION                        │
│                   "What is the WooCommerce webhook secret for SLC?"          │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │   ADMISSION & SECURITY GATE │
                        │ • Anti-Prompt Injection     │
                        │ • Near-Duplicate Filter     │
                        │ • Salience Scoring Heuristic│
                        └──────────────┬──────────────┘
                                       │
     ┌─────────────────────────────────┼─────────────────────────────────┐
     ▼                                 ▼                                 ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│   HIERARCHICAL VECTOR   │ │   FULL-TEXT KEYWORD     │ │   GRAPH RELATIONSHIPS   │
│   (pgvector Cosine)     │ │   (PostgreSQL tsvector) │ │   (Recursive CTEs)      │
│   Scope: [ecommerce]    │ │   Scope: [ecommerce]    │ │   [[wiki-links]]        │
└────────────┬────────────┘ └────────────┬────────────┘ └────────────┬────────────┘
             │                           │                           │
             └───────────────────────────┼───────────────────────────┘
                                         ▼
                     ┌───────────────────────────────────────┐
                     │   RECIPROCAL RANK FUSION (RRF) ENGINE │
                     │ • Merges Vector, Keyword & Graph Rank │
                     │ • Weighted by Dynamic Salience Score  │
                     │ • Touches `last_accessed_at` Timestamp│
                     └───────────────────┬───────────────────┘
                                         │
     ┌───────────────────────────────────┼───────────────────────────────────┐
     ▼                                   ▼                                   ▼
┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐
│  HUMAN OBSIDIAN VAULT    │ │  ISOLATED POSTGRES DB    │ │  AUDIT & TIMELINE LOG    │
│  Plain .md with YAML     │ │  Per-agent pgvector DB   │ │  Chronological Activity  │
│  Git-diffable & readable │ │  Version Snapshots       │ │  Ebbinghaus Decay Engine │
└──────────────────────────┘ └──────────────────────────┘ └──────────────────────────┘
```

---

## ✨ Key Features

* 🏛️ **Hierarchical Scoping (Wing & Room Taxonomy):** Partition memories into Wings (Projects/Domains) and Rooms (Topics). Toy's frontend React code never contaminates Candy's marketing searches.
* 📜 **Verbatim Session Ingestion:** Auto-chunk and index full conversation transcripts without lossy summarization. Retrieve exact code and terminal outputs with 100% fidelity.
* ⏳ **Ebbinghaus Temporal Decay:** Memories you use frequently remain top-of-mind; unused memories gracefully decay over time via exponential forgetting curves `salience * (0.95 ^ days)` and archive safely.
* 🔄 **Memory Versioning & Snapshots:** Updating a memory archives the previous version into `note_versions`. Roll back or inspect changes at any time with `memory_history`.
* 🛡️ **Zero External API Cost:** Runs local `sentence-transformers` embeddings on CPU/GPU. Zero API tokens spent on indexing or retrieval.
* 📖 **Obsidian Markdown Vault:** All memories are human-readable `.md` files with YAML frontmatter. Open them directly in Obsidian.
* 🔌 **Universal MCP Compliance:** Exposes 7 standard JSON-RPC tools compatible with Claude Desktop, Claude Code, Cursor IDE, OpenCode, and Hermes Agent.

---

## 📊 Feature Matrix & Benchmarks

| Feature | Mnemosyne v3.0 | Mem0 | MemPalace | Standard RAG |
|---|:---:|:---:|:---:|:---:|
| **Storage Paradigm** | **Graph + Vector + Markdown** | Vector / Graph | ChromaDB Flat | Flat Vector |
| **Hierarchical Scoping (Wing/Room)** | ✅ **Native** | ❌ Flat User ID | ✅ Wings/Rooms | ❌ Flat Namespace |
| **Verbatim Ingestion (No Lossy Summaries)** | ✅ **Yes** | ❌ Summarized | ✅ Verbatim | ❌ Chunk Only |
| **Temporal Forgetting Curve (Decay)** | ✅ **Dynamic** | ❌ Static | ✅ Basic | ❌ None |
| **Memory Version History & Diff** | ✅ **Full Snapshots** | ❌ Overwrite | ❌ None | ❌ None |
| **Timeline Activity Feed** | ✅ **Built-in** | ❌ | ❌ | ❌ |
| **Human-Readable Storage** | ✅ **Obsidian Vault** | ❌ DB Only | ❌ DB Only | ❌ DB Only |
| **Embedding API Cost** | **$0.00 (Local)** | Paid API | $0.00 (Local) | Paid API |
| **Multi-Agent Database Isolation** | ✅ **Multi-Tenant** | ⚠️ Partial | ❌ Single | ❌ Single |
| **Standard MCP Server** | ✅ **7 Tools** | ⚠️ Limited | ❌ Script only | ❌ |

---

## 🚀 30-Second Quickstart

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/M4F-S/mnemosyne.git
cd mnemosyne

# Launch PostgreSQL with pgvector
docker-compose up -d

# Verify system health
docker exec -it mnemosyne-postgres psql -U mnemosyne -d mnemosyne -c "\dt"
```

### Option 2: Python Library

```bash
pip install -e .
```

```python
from mnemosyne.core import UnifiedMemorySystem

# Initialize memory engine
memory = UnifiedMemorySystem()

# 1. Store a memory with hierarchical scope
memory.remember(
    title="PostgreSQL Production Cluster Setup",
    content="Primary cluster operates at 172.16.8.2:5432 with pgvector 0.7 enabled.",
    tags=["infra", "database"],
    wing="devops",
    room="databases",
    salience=0.9
)

# 2. Scoped hybrid retrieval
results = memory.recall(
    query="Where is the postgres cluster running?",
    mode="hybrid", # Merges semantic similarity + keyword tsvector + graph links
    scope={"wing": "devops"}
)

print(results[0]["title"], "->", results[0]["content"])
```

---

## 🔌 Model Context Protocol (MCP) Quickstarts

Mnemosyne exposes a high-performance JSON-RPC MCP server with 7 production tools:
1. `memory_remember` — Store facts, architecture decisions, and observations with `wing`/`room` tags.
2. `memory_recall` — Hybrid search (semantic + full-text + graph) with optional `scope` filters.
3. `memory_ingest_session` — Verbatim chunking and storage of full conversation logs.
4. `memory_timeline` — Chronological audit feed of recent memory activity.
5. `memory_history` — Version history of edited notes.
6. `memory_remind_me` — Prospective memory scheduling (one-time or recurring).
7. `memory_audit` — Real-time memory health, active wings, and storage metrics.

### 1. Claude Desktop Configuration
Add this to your `claude_desktop_config.json` (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python3",
      "args": ["-m", "mnemosyne.mcp_server"],
      "env": {
        "MEMORY_DB_DSN": "postgresql://mnemosyne:mnemosyne@localhost:5432/mnemosyne",
        "MEMORY_VAULT_PATH": "/Users/yourname/Documents/Obsidian/AgentVault"
      }
    }
  }
}
```

### 2. Claude Code CLI
```bash
claude mcp add mnemosyne python3 -m mnemosyne.mcp_server
```

### 3. Cursor IDE Setup
Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python3",
      "args": ["-m", "mnemosyne.mcp_server"],
      "env": {
        "MEMORY_DB_DSN": "postgresql://mnemosyne:mnemosyne@localhost:5432/mnemosyne"
      }
    }
  }
}
```

### 4. Hermes Agent Configuration (`config.yaml`)
```yaml
mcp_servers:
  obsidian_memory:
    command: /opt/data/mcp-servers/venv/bin/python
    args: [/opt/data/mcp-servers/obsidian_memory_mcp.py]
    env:
      MEMORY_DB_DSN: postgresql://mnemosyne:mnemosyne@172.16.8.2:5432/toy_db
      MEMORY_VAULT_PATH: /root/.hermes/vault
```

---

## 🛠️ CLI Usage

Mnemosyne includes a full-featured CLI:

```bash
# Remember something
mnemosyne remember "Stripe Webhook Key" "whsec_99482..." --wing payments --room stripe

# Scoped recall
mnemosyne recall "webhook secret" --wing payments

# View timeline
mnemosyne timeline --limit 10

# Run sleep consolidation & temporal decay
mnemosyne consolidate

# Get system statistics
mnemosyne stats
```

---

## 🧪 Testing

```bash
# Run unit and integration tests
pytest tests/ -v
```

---

## 🤝 Contributing & License

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on code style, testing, and pull requests.

Distributed under the **Apache 2.0 License**. See `LICENSE` for more information.

---

<div align="center">
  <sub>Built with ❤️ for autonomous AI agents everywhere. Star ⭐ this repo if Mnemosyne saved your agents from context bloat!</sub>
</div>
