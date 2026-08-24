# Mnemosyne 🧠

[![CI](https://github.com/M4F-S/mnemosyne/actions/workflows/ci.yml/badge.svg)](https://github.com/M4F-S/mnemosyne/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/mnemosyne-memory.svg)](https://pypi.org/project/mnemosyne-memory/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Local hierarchical memory engine for AI agents.**

Mnemosyne equips AI agents (Hermes, OpenClaw, OpenManus, Claude Desktop, Cursor, OpenHands, CrewAI) with persistent long-term memory. It bridges human-readable **Obsidian Markdown Vaults** with **PostgreSQL + pgvector** (or zero-config **SQLite**), powering hybrid Reciprocal Rank Fusion (RRF) search, wikilink knowledge graphs, and Ebbinghaus temporal decay.

---

## ⚡ Key Capabilities

* **🤖 MCP Native (Model Context Protocol):** Standardized stdio protocol server compatible with Claude Desktop, Claude Code, Cursor, Windsurf, OpenClaw, and Hermes.
* **🔎 High-Recall HNSW & Hybrid RRF Retrieval:** Combines dense vector similarity (`all-MiniLM-L6-v2` / `FastEmbed ONNX`) indexed with `pgvector HNSW (vector_cosine_ops)`, PostgreSQL GIN full-text search (`tsvector`), and recursive graph traversal into a single salience-weighted ranking.
* **🌐 Cross-Agent Shared Memory Layer:** Enables autonomous multi-agent fleets to publish sanitized, vetted findings to a global shared memory (`shared_db`) with strict regex credential screening.
* **☁️ Asynchronous Google Drive Synchronization:** Local-first bidirectional sync engine supporting Google Cloud Service Accounts and OAuth2 tokens with MD5 checksum verification and conflict branch preservation.
* **🏛️ Hierarchical Wing & Room Scoping:** Segment memories by domains (`wing`) and projects/channels (`room`), preventing context cross-contamination across multi-agent fleets.
* **⏳ Ebbinghaus Temporal Decay with Pinned Immunity:** Automatically decays stale memories over time while preserving critical system notes marked `pinned=True` or tagged `pinned`/`permanent`/`core`.
* **📖 Obsidian Markdown Vault Synchronization:** Every memory is written as an Obsidian-compatible `.md` note with YAML frontmatter and `[[Wikilinks]]`, allowing developers to browse agent thoughts natively in Obsidian.
* **🔄 Zero-Dependency SQLite Fallback:** Seamlessly operates in standalone SQLite mode when PostgreSQL is not available, with 100% feature parity.
* **📜 Turn-Aware Session Ingestion:** Intelligently splits and records long conversational transcripts along turn boundaries without breaking code blocks or stack traces.

---

## 🏗️ Architecture

```
                               ┌─────────────────────────────┐
                               │   AI Agents & Frameworks    │
                               │  Hermes / OpenClaw / Manus  │
                               │  Claude / Cursor / CrewAI   │
                               └──────────────┬──────────────┘
                                              │ MCP / SDK
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 Mnemosyne Core (v3.1)                                    │
│                                                                                          │
│  ┌────────────────────────┐  ┌─────────────────────────┐  ┌───────────────────────────┐  │
│  │ Admission & Security   │  │   Embedder (MiniLM)     │  │   Turn-Aware Ingestor     │  │
│  │ Injection & Size Guard │  │   384-dim Dense Vectors │  │   Conversational Splitting│  │
│  └────────────────────────┘  └─────────────────────────┘  └───────────────────────────┘  │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         Hybrid RRF Ranker & Graph Crawler                          │  │
│  │              Dense Semantic (1.0) + Keyword (0.8) + Graph (0.6) + Salience (0.2)   │  │
│  └────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
      ┌─────────────────────────────┐                   ┌─────────────────────────────┐
      │     PostgreSQL / pgvector   │                   │    Obsidian Markdown Vault  │
      │   (or SQLite 3 Fallback)    │                   │   Human-Readable Zettelkasten│
      │  - vector(384) cosine index │                   │  - YAML Frontmatter & Tags  │
      │  - GIN tsvector English tsv │                   │  - [[Wikilink]] Connections │
      │  - Wing / Room Scoping      │                   │  - Graph View Visualizer    │
      │  - Version Snapshots & Logs │                   │                             │
      └─────────────────────────────┘                   └─────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Installation

```bash
# Install from PyPI
pip install mnemosyne-memory

# Or install from source
git clone https://github.com/M4F-S/mnemosyne.git
cd mnemosyne
pip install -e ".[dev]"
```

### 2. Run with Docker (Recommended)

Start the PostgreSQL + pgvector database:

```bash
docker compose up -d
```

### 3. Run MCP Server

```bash
# PostgreSQL backend
MEMORY_DB_DSN="postgresql://mnemosyne:mnemosyne@localhost:5432/agent_db" python3 -m mnemosyne server

# Zero-config local SQLite backend
MEMORY_VAULT_PATH="~/.mnemosyne/vault" python3 -m mnemosyne server
```

---

## 🤖 Agent Framework Integrations

Mnemosyne connects to all major AI agent harnesses. Detailed guides are available in [`docs/integrations/`](docs/integrations/):

### 1. OpenClaw
Add to your `openclaw-config.yaml`:
```yaml
plugins:
  mcp_servers:
    mnemosyne:
      command: "python3"
      args: ["-m", "mnemosyne", "server"]
      env:
        MEMORY_VAULT_PATH: "~/.openclaw/vault"
        MEMORY_DEFAULT_WING: "openclaw"
```
*(See [OpenClaw Guide](docs/integrations/openclaw.md) for custom Python hooks).*

### 2. Hermes Agent
In `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  obsidian_memory:
    command: python3
    args: ["-m", "mnemosyne", "server"]
    env:
      MEMORY_DB_DSN: postgresql://mnemosyne:mnemosyne@localhost:5432/toy_db
      MEMORY_VAULT_PATH: ~/.hermes/vault
```

### 3. Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python3",
      "args": ["-m", "mnemosyne", "server"],
      "env": {
        "MEMORY_VAULT_PATH": "~/Documents/Obsidian/AgentVault",
        "MEMORY_DEFAULT_WING": "claude"
      }
    }
  }
}
```

### 4. Cursor IDE (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python3",
      "args": ["-m", "mnemosyne", "server"],
      "env": {
        "MEMORY_VAULT_PATH": "./.vault",
        "MEMORY_DEFAULT_WING": "codebase"
      }
    }
  }
}
```

### 5. Open-Manus, CrewAI & Python SDK
```python
from mnemosyne import UnifiedMemorySystem

mem = UnifiedMemorySystem(vault_path="~/.manus/vault")

# Remember facts with domain scoping and pinned immunity
mem.remember(
    title="PostgreSQL Optimization",
    content="Use ivfflat index with lists=100 for vector columns under 1M rows.",
    wing="engineering",
    room="databases",
    tags=["postgres", "pgvector"],
    pinned=True  # Immune to temporal decay
)

# Hybrid recall
results = mem.recall("vector index tips", mode="hybrid", scope={"wing": "engineering"})
for note in results:
    print(note["title"], note["content"])
```
*(See [Open-Manus & Python Guide](docs/integrations/openmanus_and_python.md) and [OpenAI Codex Guide](docs/integrations/openai_codex.md)).*

---

## 🛠️ MCP Tools Reference (8 Tools)

| Tool | Parameters | Description |
|---|---|---|
| `memory_remember` | `title`, `content`, `tags`, `wing`, `room`, `salience`, `pinned` | Store a markdown note in the vault with semantic vector embedding and decay immunity option |
| `memory_publish_shared` | `title`, `content`, `tags`, `wing`, `room` | Publish a vetted, sanitized policy or finding to the global fleet shared memory (`shared_db`) |
| `memory_recall` | `query`, `mode` (hybrid/semantic/keyword/graph), `scope`, `top_k`, `include_shared` | Retrieve memories using RRF hybrid search, pgvector HNSW, or graph traversal across private & shared stores |
| `memory_ingest_session` | `transcript`, `wing`, `room` | Chunk and ingest full conversation transcripts along turn boundaries with linear sliding-window overlap |
| `memory_timeline` | `limit` | View chronological activity timeline of memory operations |
| `memory_history` | `title`, `limit` | Inspect version snapshots and past edits of a specific note |
| `memory_remind_me` | `title`, `content`, `trigger_at`, `recurring` | Schedule prospective memory reminders |
| `memory_audit` | *(none)* | Inspect database statistics, health metrics, and active wings |

---

## 💻 CLI Usage

```bash
# Store a memory
python -m mnemosyne remember "API Architecture" "Authentication uses Bearer JWT tokens." --tags security auth --wing backend

# Publish shared memory for other fleet agents
python -m mnemosyne publish-shared "Global Production Policy" "Always check SSL certificates before deploying." --wing devops

# Recall memories
python -m mnemosyne recall "JWT authentication" --mode hybrid --wing backend

# Synchronize Obsidian Vault with Google Drive (one-off)
python -m mnemosyne sync-gdrive --credentials service-account.json

# Run Google Drive sync continuously as a background daemon
python -m mnemosyne sync-gdrive --daemon --interval 60

# View operational timeline
python -m mnemosyne timeline --limit 10

# Trigger Ebbinghaus decay consolidation
python -m mnemosyne consolidate --decay-rate 0.95 --archive-threshold 0.05

# Check system health
python -m mnemosyne stats
```

---

## 🧪 Testing

Mnemosyne includes a comprehensive test suite covering unit tests and live PostgreSQL integration tests:

```bash
# Run all unit tests
pytest tests/ -v -m "not integration"

# Run with PostgreSQL pgvector integration tests
MEMORY_DB_DSN="postgresql://mnemosyne:mnemosyne@localhost:5432/agent_db" pytest tests/ -v
```

---

## 📄 License

MIT License. Built for the open agent ecosystem.
