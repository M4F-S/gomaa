# Mnemosyne 🧠

[![CI](https://github.com/M4F-S/mnemosyne/actions/workflows/ci.yml/badge.svg)](https://github.com/M4F-S/mnemosyne/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/mnemosyne-memory.svg)](https://pypi.org/project/mnemosyne-memory/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Production-grade, local-first hierarchical memory engine for autonomous AI agents.**

Mnemosyne equips AI agents (Hermes, OpenClaw, OpenManus, Claude Desktop, Cursor, Windsurf, CrewAI, LangChain) with permanent, structured long-term memory. It bridges human-readable **Obsidian Markdown Vaults** with high-speed **PostgreSQL + pgvector (HNSW)** or zero-config **SQLite**, powering hybrid Reciprocal Rank Fusion (RRF) search, wikilink knowledge graphs, Ebbinghaus temporal decay, cross-agent fleet sharing, and asynchronous Google Drive cloud synchronization.

---

## 📑 Table of Contents

- [⚡ Complete Feature Matrix](#-complete-feature-matrix)
- [🏗️ System Architecture](#️-system-architecture)
- [🧠 Deep Dive into Key Capabilities](#-deep-dive-into-key-capabilities)
  - [1. Hierarchical Wing & Room Taxonomy](#1-hierarchical-wing--room-taxonomy)
  - [2. Hybrid Reciprocal Rank Fusion (RRF) Search](#2-hybrid-reciprocal-rank-fusion-rrf-search)
  - [3. Cross-Agent Shared Memory Layer (`shared_db`)](#3-cross-agent-shared-memory-layer-shared_db)
  - [4. Ebbinghaus Temporal Decay & Pinned Immunity](#4-ebbinghaus-temporal-decay--pinned-immunity)
  - [5. Obsidian Markdown Vault & Bi-Directional Graph](#5-obsidian-markdown-vault--bi-directional-graph)
  - [6. Turn-Aware Verbatim Session Ingestor](#6-turn-aware-verbatim-session-ingestor)
  - [7. Asynchronous Google Drive Cloud Synchronization](#7-asynchronous-google-drive-cloud-synchronization)
  - [8. Flexible Embedding Backends (FastEmbed / Microservice / Local)](#8-flexible-embedding-backends-fastembed--microservice--local)
  - [9. Defense-in-Depth Security & Injection Armor](#9-defense-in-depth-security--injection-armor)
- [🛠️ MCP Tool Reference (8 Tools)](#️-mcp-tool-reference-8-tools)
- [🌐 Multi-Agent Fleet Production Architecture](#-multi-agent-fleet-production-architecture)
- [🚀 Quick Start & Installation](#-quick-start--installation)
- [🤖 Agent Framework Integration Recipes](#-agent-framework-integration-recipes)
- [💻 Complete CLI Command Reference](#-complete-cli-command-reference)
- [⚙️ Environment Variables Reference](#️-environment-variables-reference)
- [🧪 Testing & Benchmarks](#-testing--benchmarks)
- [📄 License](#-license)

---

## ⚡ Complete Feature Matrix

| Feature | Description | Benefit |
|---|---|---|
| **🤖 MCP Native (v2024-11-05)** | Standardized stdio JSON-RPC protocol server | Seamless drop-in for Claude, Cursor, Windsurf, Hermes, OpenClaw |
| **🔎 High-Recall HNSW Vector Search** | `pgvector` HNSW indexing with `vector_cosine_ops` (`m=16, ef_construction=64`) | Sub-millisecond vector recall without clustering retraining |
| **⚖️ Hybrid RRF Retrieval** | Reciprocal Rank Fusion of Dense Embeddings (1.0) + GIN FTS (0.8) + Graph (0.6) + Salience (0.2) | Captures exact technical keywords (CVEs, code tokens) & fuzzy semantics |
| **🏛️ Wing & Room Scoping** | 2-level taxonomy (`wing` = domain/project, `room` = channel/topic) | Eliminates context window bloating & cross-domain hallucination |
| **🌐 Cross-Agent Shared Memory** | Central `shared_db` queryable across multi-agent fleets with credential screening | Collective fleet intelligence without compromising private databases |
| **☁️ Async Google Drive Sync** | Local-first bidirectional sync engine with MD5 diffing and `.conflict.md` branch resolution | Sub-millisecond agent I/O locally + automatic cloud backup & team sharing |
| **⏳ Ebbinghaus Temporal Decay** | Exponential decay $Salience_t = Salience_0 \times (0.95)^{\Delta t}$ with 90-day auto-archive | Auto-prunes transient noise while keeping active memories sharp |
| **📌 Pinned Memory Immunity** | Permanent immunity to decay via `pinned=True` or `#pinned` tags | Guarantees foundational instructions and core rules never fade |
| **📖 Obsidian Zettelkasten** | Writes human-readable Markdown notes with YAML frontmatter & `[[Wiki Links]]` | Direct visual inspection, editing, and graph visualization in Obsidian |
| **📜 Turn-Aware Ingestor** | 1,500-char sliding-window chunking with 200-char overlap along turn boundaries | Preserves entire conversation history without breaking code blocks |
| **🛡️ Prompt Injection Armor** | Neutralizes control tokens (`<|im_start|>`, `[INST]`) in prose; escapes XML context tags | Prevents memory poisoning and context hijacking attacks |
| **⚡ FastEmbed ONNX Support** | Ultra-lightweight ONNX runtime embedding engine (~30MB RAM) | 90% memory reduction vs heavy PyTorch `sentence-transformers` |
| **🔄 Zero-Config SQLite Fallback** | Automatic fallback to local SQLite when PostgreSQL is offline | 100% feature parity for standalone developer workstations |

---

## 🏗️ System Architecture

```
                                ┌──────────────────────────────────────────────┐
                                │          AI Agents & LLM Frameworks          │
                                │  Hermes • OpenClaw • Claude • Cursor • Manus │
                                └──────────────────────┬───────────────────────┘
                                                       │ JSON-RPC (stdio) / Python SDK
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           Mnemosyne Core (v3.4.0)                                           │
│                                                                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────────────────────────┐  │
│  │ Admission & Security    │  │ Multi-Backend Embedder  │  │ Turn-Aware Session Ingestor                 │  │
│  │ - Secret Regex Guard    │  │ - FastEmbed (ONNX 30MB) │  │ - Turn boundary splitting                   │  │
│  │ - Injection Neutralizer │  │ - Remote Microservice   │  │ - 1500-char linear sliding window           │  │
│  │ - Path Traversal Guard  │  │ - SentenceTransformers  │  │ - Sequential [[Wiki Link]] chaining         │  │
│  └─────────────────────────┘  └─────────────────────────┘  └─────────────────────────────────────────────┘  │
│                                                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                 Hybrid RRF Retrieval & Graph Ranker                                   │  │
│  │            RRF Score = 1.0 * Dense(HNSW) + 0.8 * Keyword(FTS) + 0.6 * Graph + 0.2 * Salience          │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────┬───────────────────────────────────────┬─────────────────────────────┘
                                        │                                       │
                ┌───────────────────────┴───────────────────────┐               │
                ▼                                               ▼               ▼
 ┌─────────────────────────────┐                 ┌─────────────────────────────────────────────┐
 │    PostgreSQL + pgvector    │                 │       Obsidian Markdown Vault (Local)       │
 │ - HNSW vector_cosine_ops    │                 │ - Human-Readable Markdown + YAML Frontmatter │
 │ - GIN tsvector English FTS  │                 │ - [[Wikilink]] Knowledge Graph Visualizer   │
 │ - Self-Healing DB Pool      │                 │ - Atomic Writes with EXDEV Fallback         │
 │ - Private DB + shared_db    │                 └──────────────────────┬──────────────────────┘
 └─────────────────────────────┘                                        │ Async Background Sync
                                                                        ▼
                                                 ┌─────────────────────────────────────────────┐
                                                 │              Google Drive Cloud             │
                                                 │ - Service Account / OAuth2 Authentication    │
                                                 │ - MD5 Checksum Verification                 │
                                                 │ - Sibling .conflict-TIMESTAMP.md Resolution │
                                                 └─────────────────────────────────────────────┘
```

---

## 🧠 Deep Dive into Key Capabilities

### 1. Hierarchical Wing & Room Taxonomy
Memory cross-contamination is a major failure mode in multi-agent fleets. Mnemosyne structures memory as a 2-level physical palace:
* **`wing` (Domain/Project):** Top-level domain boundary (e.g. `ecommerce`, `pentest`, `devops`, `shared`).
* **`room` (Topic/Channel):** Granular topic partition (e.g. `database`, `firewall`, `stripe_api`).

Queries can be scoped tightly to a specific wing or room, preventing marketing prompts from recalling penetration testing findings.

### 2. Hybrid Reciprocal Rank Fusion (RRF) Search
Standard vector search fails on exact technical strings (e.g. `CVE-2024-38077`, `0x7fff5fbff8c0`), while keyword search fails on semantic concepts. Mnemosyne executes multi-candidate retrieval and merges results using weighted RRF:

$$\text{RRF Score}(d) = \sum_{m \in \text{modes}} w_m \cdot \frac{1}{k + \text{rank}_m(d)} + 0.2 \cdot \text{Salience}(d)$$

* **Dense HNSW Vector Search:** Weight $1.0$ (Cosine distance over 384-dimensional embeddings).
* **PostgreSQL Full-Text Search:** Weight $0.8$ (`tsvector` weighted with title as `A` and content as `B`).
* **Recursive Graph Traversal:** Weight $0.6$ (Recursive CTE discovering 1-hop and 2-hop `[[Wiki Links]]`).
* **Memory Salience Engine:** Weight $0.2$ (Importance score from $0.0$ to $1.0$).

### 3. Cross-Agent Shared Memory Layer (`shared_db`)
In autonomous multi-agent environments, agents maintain isolated private databases (`toy_db`, `old_db`, `candy_db`, etc.) to prevent state corruption. However, collective intelligence requires sharing global policies and verified facts.
* **Publishing:** Using `memory_publish_shared`, vetted notes are published to `shared_db`.
* **Credential Screening:** Content is scanned against strict regex filters for Anthropic keys (`sk-ant-`), Google Gemini keys (`AIza...`), HuggingFace tokens (`hf_...`), OpenAI keys (`sk-proj-...`), AWS access keys (`AKIA...`), Slack tokens (`xox-`), and private keys.
* **Fail-Soft Recall:** When an agent queries memory, `memory_recall` queries both the private store and `shared_db`. If the shared database is temporarily unreachable, it degrades gracefully without interrupting the agent.

### 4. Ebbinghaus Temporal Decay & Pinned Immunity
Memories naturally lose relevance over time. Mnemosyne implements Herman Ebbinghaus's exponential forgetting curve:

$$\text{Salience}(t) = \text{Salience}_0 \times (0.95)^{\Delta t_{\text{days}}}$$

* **Touch Feedback:** Accessing a memory updates `last_accessed_at`, resetting its decay.
* **Nightly Auto-Archiving:** Consolidation automatically transitions notes with $\text{Salience} < 0.05$ and unaccessed for $>90\text{ days}$ to `status = 'archived'`.
* **Pinned Immunity:** System rules, core policies, or notes marked with `pinned=True` or tagged `#pinned` receive permanent immunity from temporal decay ($\text{Salience} = 1.0$).

### 5. Obsidian Markdown Vault & Bi-Directional Graph
Every memory created by an agent is simultaneously written as a human-readable `.md` file inside your Obsidian vault:
* **Zettelkasten Frontmatter:** Contains `title`, `date`, `tags`, `type`, `salience`, `wing`, and `room`.
* **Knowledge Graph:** Target notes mentioned as `[[Target Note]]` are automatically parsed into bi-directional edges in PostgreSQL.
* **Live Inspection:** Open Obsidian on your desktop or mobile device and explore your agent fleet's collective memory in Obsidian's interactive Graph View.

### 6. Turn-Aware Verbatim Session Ingestor
Conversational transcripts often contain crucial nuances lost in lossy summarization. `memory_ingest_session`:
* Splits raw transcripts along turn boundaries (`User:`, `Assistant:`, `### Turn`, `**Human**:`).
* For turns longer than 1,500 characters, applies a **linear sliding window** (1,500 chars with 200-char overlap).
* Chains sequential chunks using `[[Session ... Turn 01 Part 02]]` wikilinks, preserving code blocks, execution traces, and conversational flow.

### 7. Asynchronous Google Drive Cloud Synchronization
Keep your agent vaults securely backed up and synchronized across multiple machines or mobile devices:
* **Local-First Speed:** Agent tool calls execute at local SSD speeds (<1ms) without blocking on Google Drive network latency.
* **Background Daemon / Cron Sync:** Scans vault files, computes MD5 checksums, and synchronizes deltas bidirectionally with Google Drive.
* **Conflict Resolution:** If a file is modified on both Google Drive and the local agent vault simultaneously, Mnemosyne saves the incoming version as `NoteName.conflict-YYYYMMDD-HHMMSS.md`, preventing data loss.
* **Authentication:** Supports Google Cloud Service Account JSON (`GOOGLE_APPLICATION_CREDENTIALS`, `GDRIVE_SERVICE_ACCOUNT_JSON`) and OAuth2 user tokens (`GDRIVE_TOKEN_JSON`).

### 8. Flexible Embedding Backends (FastEmbed / Microservice / Local)
Mnemosyne adapts to any deployment resource budget:
1. **FastEmbed ONNX Runtime (Recommended for Standalone Nodes):** Uses ONNX Runtime C++ execution (~30MB RAM). Zero PyTorch overhead.
2. **Centralized Microservice (`mnemosyne.embed_service`):** Hosts sentence-transformers in a single dedicated container serving multiple agent containers over HTTP (`MEMORY_EMBED_URL`).
3. **Local SentenceTransformers:** Standalone PyTorch execution (`all-MiniLM-L6-v2`, 384-dimensional).
4. **Deterministic Hash Fallback:** Zero-RAM mathematical vector hash for ultra-constrained environments.

### 9. Defense-in-Depth Security & Injection Armor
* **Path Traversal Immunity:** Dual-resolved canonical path checks (`is_relative_to`) ensure file operations cannot escape the vault root.
* **Atomic Sibling Writes:** Files are written to sibling temporary files (`.note.pid.tmp`) and renamed atomically, with automatic fallback for `EXDEV` cross-device volume mounts.
* **Control Token Neutralization:** Neutralizes LLM injection tokens (`<|im_start|>`, `<|system|>`, `[INST]`, `<<SYS>>`) in prose while preserving code blocks verbatim.
* **Structured XML Context Enclosure:** Recalled memories are wrapped in `<recalled_memory_context id="..." title="..." source="...">` tags with internal tag escaping, ensuring host LLMs never confuse recalled memories with active system directives.

---

## 🛠️ MCP Tool Reference (8 Tools)

All 8 tools are natively exposed to agents over standard MCP JSON-RPC stdio:

### 1. `memory_remember`
Store a private memory note in the vault with semantic embedding, tags, and hierarchical scoping.
```json
{
  "title": "PostgreSQL HNSW Tuning",
  "content": "For datasets >10,000 vectors, use HNSW with m=16 and ef_construction=64 for optimal recall.",
  "tags": ["database", "pgvector", "performance"],
  "wing": "engineering",
  "room": "databases",
  "salience": 0.8,
  "pinned": true
}
```

### 2. `memory_publish_shared`
Publish a sanitized, vetted finding or policy to the cross-agent shared fleet memory (`shared_db`).
```json
{
  "title": "Fleet Security Policy: SSL Verification",
  "content": "All internal agent HTTP requests must enforce SSL certificate validation.",
  "tags": ["security", "policy"],
  "wing": "shared",
  "room": "general"
}
```

### 3. `memory_recall`
Search memories across private and shared fleet databases using hybrid RRF, HNSW vectors, keywords, or graph.
```json
{
  "query": "HNSW index configuration parameters",
  "mode": "hybrid",
  "top_k": 5,
  "scope": {
    "wing": "engineering",
    "room": "databases"
  },
  "include_shared": true
}
```

### 4. `memory_ingest_session`
Ingest and chunk a complete conversation transcript verbatim along turn boundaries.
```json
{
  "transcript": "User: How do we configure pgvector?\nAssistant: Use CREATE EXTENSION vector; then create an HNSW index.",
  "wing": "engineering",
  "room": "sessions"
}
```

### 5. `memory_timeline`
Inspect recent memory operations (remember, recall, remind, consolidate) in chronological order.
```json
{
  "limit": 20
}
```

### 6. `memory_history`
View version history and past edit snapshots of a specific memory note before updates.
```json
{
  "title": "PostgreSQL HNSW Tuning",
  "limit": 5
}
```

### 7. `memory_remind_me`
Schedule a future prospective reminder or recurring task.
```json
{
  "title": "Rotate Database Credentials",
  "content": "Verify that all 5 agent connection pools are refreshed with new passwords.",
  "trigger_at": "2026-09-01T00:00:00Z",
  "recurring": "monthly"
}
```

### 8. `memory_audit`
Get real-time memory health metrics, store backend status, request counts, and active wings.
```json
{}
```

---

## 🌐 Multi-Agent Fleet Production Architecture

In multi-agent production setups (such as the 5-agent Hermes fleet), Mnemosyne isolates agent databases on an internal Docker network while providing shared intelligence:

```
                                  ┌─────────────────────────────────────────┐
                                  │      Production VPS (${VPS_HOST})      │
                                  └────────────────────┬────────────────────┘
                                                       │
         ┌───────────────────┬──────────────────┼───────────────────┬──────────────────┐
         ▼                   ▼                  ▼                   ▼                  ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
│   hermes-agent   ││ hermes-assistant ││ hermes-marketing ││  hermes-pentest  ││  hermes-trader   │
│      (Toy)       ││      (Old)       ││     (Candy)      ││     (Pencil)     ││      (Coin)      │
│   Database:      ││   Database:      ││   Database:      ││   Database:      ││   Database:      │
│     toy_db       ││     old_db       ││     candy_db     ││     pencil_db    ││     trader_db    │
└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘
         │                   │                  │                   │                  │
         └───────────────────┴──────────────────┼───────────────────┴──────────────────┘
                                                │
                                                ▼
                               ┌───────────────────────────────────┐
                               │   PostgreSQL + pgvector (HNSW)    │
                               │   - Private DBs: toy_db, old_db.. │
                               │   - Shared DB:   shared_db        │
                               └───────────────────────────────────┘
```

---

## 🚀 Quick Start & Installation

### 1. Installation

```bash
# Standard installation
pip install mnemosyne-memory

# With Google Drive Cloud Synchronization support
pip install "mnemosyne-memory[gdrive]"

# With lightweight FastEmbed ONNX support (~30MB RAM)
pip install "mnemosyne-memory[fastembed]"

# Full installation (All extras + Dev dependencies)
pip install "mnemosyne-memory[dev,gdrive,fastembed,embed-service]"
```

### 2. Run with Docker Compose

Start the PostgreSQL + `pgvector` container:
```bash
docker compose up -d
```

### 3. Launch MCP Server

```bash
# Standalone with local SQLite (Zero configuration)
python -m mnemosyne server

# With PostgreSQL + pgvector
MEMORY_DB_DSN="postgresql://mnemosyne:***@localhost:5432/my_agent_db" python -m mnemosyne server
```

---

## 🤖 Agent Framework Integration Recipes

### 1. Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python3",
      "args": ["-m", "mnemosyne", "server"],
      "env": {
        "MEMORY_VAULT_PATH": "/Users/username/Documents/Obsidian/AgentVault",
        "MEMORY_DEFAULT_WING": "claude"
      }
    }
  }
}
```

### 2. Cursor IDE (`.cursor/mcp.json`)
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

### 3. Hermes Agent (`~/.hermes/config.yaml`)
```yaml
mcp_servers:
  obsidian_memory:
    command: python3
    args: ["-m", "mnemosyne", "server"]
    env:
      MEMORY_DB_DSN: "postgresql://mnemosyne:***@${DB_HOST}:5432/toy_db"
      MEMORY_SHARED_DSN: "postgresql://mnemosyne:***@${DB_HOST}:5432/shared_db"
      MEMORY_VAULT_PATH: "/opt/data/vault"
```

### 4. OpenClaw (`openclaw-config.yaml`)
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

### 5. Python SDK & Autonomous Agent Scripts
```python
from mnemosyne import UnifiedMemorySystem

mem = UnifiedMemorySystem(
    vault_path="~/.agent/vault",
    dsn="postgresql://mnemosyne:***@localhost:5432/agent_db",
    shared_dsn="postgresql://mnemosyne:***@localhost:5432/shared_db"
)

# Remember fact
mem.remember(
    title="Kubernetes Cluster Policy",
    content="Deployments in staging must specify resource memory limits.",
    wing="infrastructure",
    room="k8s",
    tags=["kubernetes", "policy"],
    pinned=True
)

# Hybrid recall
results = mem.recall(
    query="staging memory limits",
    mode="hybrid",
    scope={"wing": "infrastructure"}
)

for r in results:
    print(r["title"], "->", r["formatted_context"])
```

---

## 💻 Complete CLI Command Reference

Mnemosyne includes a full-featured management CLI:

```bash
# 1. Store a memory note
python -m mnemosyne remember "API Architecture" "Uses Bearer JWT auth." --tags security auth --wing backend --room api --salience 0.8 --pinned

# 2. Publish shared fleet memory
python -m mnemosyne publish-shared "Global Production Policy" "Always check SSL certs." --wing devops

# 3. Search memories
python -m mnemosyne recall "JWT authentication" --mode hybrid --top-k 5 --wing backend

# 4. View activity timeline
python -m mnemosyne timeline --limit 20

# 5. Trigger Ebbinghaus decay & link reconciliation
python -m mnemosyne consolidate --decay-rate 0.95 --archive-threshold 0.05

# 6. Check system statistics & health
python -m mnemosyne stats

# 7. Synchronize with Google Drive (One-off pass)
python -m mnemosyne sync-gdrive --folder "My-Agent-Vault" --credentials service-account.json

# 8. Run Google Drive Sync as a background daemon
python -m mnemosyne sync-gdrive --daemon --interval 60

# 9. Run standalone Centralized Embedding Microservice
python -m mnemosyne embed-service --host 0.0.0.0 --port 8000 --model all-MiniLM-L6-v2
```

---

## ⚙️ Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `MEMORY_VAULT_PATH` | `~/.mnemosyne/vault` | Filesystem path to the local Obsidian Markdown vault directory |
| `MEMORY_DB_DSN` | *(none)* | PostgreSQL DSN (e.g. `postgresql://user:pass@host:5432/db`). If unset, uses SQLite |
| `MEMORY_SHARED_DSN` | *(none)* | PostgreSQL DSN for the optional cross-agent shared fleet database |
| `MEMORY_AGENT_NAME` | `local-agent` | Identifier for the origin agent in multi-agent fleet deployments |
| `MEMORY_EMBED_URL` | *(none)* | URL of remote centralized embedding microservice (e.g. `http://localhost:8000`) |
| `MEMORY_REQUIRE_POSTGRES` | `false` | Set `true` to raise an error instead of falling back to SQLite if PostgreSQL fails |
| `GOOGLE_APPLICATION_CREDENTIALS` | *(none)* | File path to Google Cloud Service Account JSON for Google Drive synchronization |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | *(none)* | Stringified JSON content of Google Cloud Service Account credentials |
| `GDRIVE_TOKEN_JSON` | *(none)* | Stringified JSON content of authorized Google OAuth2 user token |
| `TOKENIZERS_PARALLELISM` | `false` | Disables HuggingFace tokenizer forks to preserve stdio JSON-RPC stream integrity |
| `HF_HUB_DISABLE_PROGRESS_BARS` | `1` | Disables progress bars in stdio to keep MCP streams pristine |
| `HF_HUB_OFFLINE` | `0` | Set `1` to run SentenceTransformers 100% offline using local cache |
| `TRANSFORMERS_OFFLINE` | `0` | Set `1` to prevent transformers from making external HuggingFace network requests |

---

## 🧪 Testing & Benchmarks

Mnemosyne maintains a comprehensive test suite (unit tests, security injection tests, SQLite tests, and live PostgreSQL pgvector integration tests):

```bash
# Run all unit tests
pytest tests/ -v -m "not integration"

# Run full test suite including live PostgreSQL + pgvector tests
MEMORY_DB_DSN="postgresql://mnemosyne:***@localhost:5432/test_db" pytest tests/ -v
```

---

## 📄 License

Apache-2.0 License. Built for the open autonomous agent ecosystem. See [LICENSE](LICENSE) for full details.
