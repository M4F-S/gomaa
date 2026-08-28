# Gomaa 🧠

[![CI](https://github.com/M4F-S/gomaa/actions/workflows/ci.yml/badge.svg)](https://github.com/M4F-S/gomaa/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/gomaa.svg)](https://pypi.org/project/gomaa/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Production-grade, local-first hierarchical memory engine for autonomous AI agents.**

Gomaa equips AI agents (Hermes, OpenClaw, OpenManus, Claude Desktop, Cursor, Windsurf, CrewAI, LangChain) with permanent, structured long-term memory. It bridges human-readable **Obsidian Markdown Vaults** with high-speed **PostgreSQL + pgvector (HNSW)** or zero-config **SQLite**, powering hybrid Reciprocal Rank Fusion (RRF) search, wikilink knowledge graphs, Ebbinghaus temporal decay, cross-agent fleet sharing, and asynchronous Google Drive cloud synchronization.

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
- [🛠️ MCP Tool Reference (9 Tools)](#️-mcp-tool-reference-9-tools)
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
| **🎨 Native Aurora Dashboard** | Zero-dependency embedded web knowledge graph (`gomaa dashboard`) | Real-time visual memory graph, 5-layer distribution charts & live query sandbox |
| **🧠 5 Cognitive Memory Layers** | Scientific classification (Episodic, Semantic, Procedural, Social, Preferential) | Eliminates cross-domain noise and structures long-term agent understanding |
| **📦 Token-Budgeted Assembler** | Packs top-salience memories into exact LLM prompt budgets with XML escaping | Direct drop-in context injection for LLM system prompts without overflow |
| **🔌 Framework Adapters** | Native integrations for LangChain, LangGraph, and CrewAI | Drop-in multi-agent swarm memory with zero boilerplate |
| **🔄 Zero-Config SQLite Light Mode** | Automatic fallback to local SQLite WAL when PostgreSQL is offline | 5-second setup with 100% feature parity for standalone developer workstations |

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
│                                           Gomaa Core (v3.4.0)                                           │
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
Memory cross-contamination is a major failure mode in multi-agent fleets. Gomaa structures memory as a 2-level physical palace:
* **`wing` (Domain/Project):** Top-level domain boundary (e.g. `ecommerce`, `pentest`, `devops`, `shared`).
* **`room` (Topic/Channel):** Granular topic partition (e.g. `database`, `firewall`, `stripe_api`).

Queries can be scoped tightly to a specific wing or room, preventing marketing prompts from recalling penetration testing findings.

### 2. Hybrid Reciprocal Rank Fusion (RRF) Search
Standard vector search fails on exact technical strings (e.g. `CVE-2024-38077`, `0x7fff5fbff8c0`), while keyword search fails on semantic concepts. Gomaa executes multi-candidate retrieval and merges results using weighted RRF:

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
Memories naturally lose relevance over time. Gomaa implements Herman Ebbinghaus's exponential forgetting curve:

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
* **Conflict Resolution:** If a file is modified on both Google Drive and the local agent vault simultaneously, Gomaa saves the incoming version as `NoteName.conflict-YYYYMMDD-HHMMSS.md`, preventing data loss.
* **Authentication:** Supports Google Cloud Service Account JSON (`GOOGLE_APPLICATION_CREDENTIALS`, `GDRIVE_SERVICE_ACCOUNT_JSON`) and OAuth2 user tokens (`GDRIVE_TOKEN_JSON`).

### 8. Flexible Embedding Backends (FastEmbed / Microservice / Local)
Gomaa adapts to any deployment resource budget:
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

### 8. `memory_assemble_context`
Retrieve, rank, and pack high-salience memories into a strict token-budgeted XML prompt block ready for direct LLM system prompt injection.
```json
{
  "query": "Kubernetes staging deployment limits",
  "max_tokens": 1500,
  "mode": "hybrid",
  "scope": {
    "wing": "infrastructure"
  },
  "include_shared": true
}
```

### 9. `memory_audit`
Get real-time memory health metrics, store backend status, request counts, and active wings.
```json
{}
```

---

## 🌐 Multi-Agent Fleet Production Architecture

In multi-agent production setups (such as the 5-agent Hermes fleet), Gomaa isolates agent databases on an internal Docker network while providing shared intelligence:

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
pip install gomaa

# With Google Drive Cloud Synchronization support
pip install "gomaa[gdrive]"

# With lightweight FastEmbed ONNX support (~30MB RAM)
pip install "gomaa[fastembed]"

# Full installation (All extras + Dev dependencies)
pip install "gomaa[dev,gdrive,fastembed,embed-service]"
```

### 2. Run with Docker Compose

Start the PostgreSQL + `pgvector` container:
```bash
docker compose up -d
```

### 3. Launch MCP Server

```bash
# Standalone with local SQLite (Zero configuration)
python -m gomaa server

# With PostgreSQL + pgvector
MEMORY_DB_DSN="postgresql://mnemosyne:***@localhost:5432/my_agent_db" python -m gomaa server
```

---

## 🤖 Agent Framework Integration Recipes

### 1. Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "gomaa": {
      "command": "python3",
      "args": ["-m", "gomaa", "server"],
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
    "gomaa": {
      "command": "python3",
      "args": ["-m", "gomaa", "server"],
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
    args: ["-m", "gomaa", "server"]
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
      args: ["-m", "gomaa", "server"]
      env:
        MEMORY_VAULT_PATH: "~/.openclaw/vault"
        MEMORY_DEFAULT_WING: "openclaw"
```

### 5. LangChain & LangGraph
Drop-in memory adapter using Gomaa's token-budgeted prompt context assembler:
```python
from gomaa.adapters.langchain import GomaaMemory
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI

memory = GomaaMemory(
    wing="support_agent",
    room="tickets",
    max_tokens=1500
)

conversation = ConversationChain(
    llm=ChatOpenAI(model="gpt-4o"),
    memory=memory,
    verbose=True
)
conversation.predict(input="Our PostgreSQL server is at 10.0.0.5 on port 5432.")
```

### 6. CrewAI Multi-Agent Swarms
Domain-isolated memory handler for CrewAI agents:
```python
from gomaa.adapters.crewai import GomaaMemoryHandler
from crewai import Agent, Crew, Task

mem_handler = GomaaMemoryHandler(crew_name="security_squad")

agent = Agent(
    role="Penetration Tester",
    goal="Discover vulnerabilities in staging infrastructure",
    memory=True
)

# Save task findings with automatic domain wing isolation
mem_handler.save(
    value="Port 8080 open on staging host 10.0.0.5 running vulnerable Tomcat",
    metadata={"task": "recon", "salience": 0.9, "pinned": True},
    agent_role="Penetration Tester"
)
```

### 7. Python SDK & Autonomous Agent Scripts
```python
from gomaa import UnifiedMemorySystem

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

# Assemble token-budgeted context for LLM prompt
ctx = mem.assemble_context(
    query="staging memory limits",
    max_tokens=1500,
    scope={"wing": "infrastructure"}
)
print(ctx["context_text"])
```

---

## 💻 Complete CLI Command Reference

Gomaa includes a full-featured management CLI:

```bash
# 1. Initialize local vault & generate ready-to-copy MCP configurations
gomaa init --path ~/.mnemosyne/vault

# 2. Launch interactive Aurora Web Knowledge Graph Dashboard
gomaa dashboard --port 8765

# 3. Store a memory note
gomaa remember "API Architecture" "Uses Bearer JWT auth." --tags security auth --wing backend --room api --salience 0.8 --pinned

# 4. Publish shared fleet memory
gomaa publish-shared "Global Production Policy" "Always check SSL certs." --wing devops

# 5. Search memories (hybrid / semantic / keyword / graph)
gomaa recall "JWT authentication" --mode hybrid --top-k 5 --wing backend

# 6. Assemble token-budgeted prompt context block
gomaa assemble-context "production policy" --max-tokens 1500 --wing devops

# 7. View activity timeline
gomaa timeline --limit 20

# 8. Trigger Ebbinghaus decay & link reconciliation
gomaa consolidate --decay-rate 0.95 --archive-threshold 0.05

# 9. Check system statistics & health
gomaa stats

# 10. Synchronize with Google Drive (One-off pass or daemon mode)
gomaa sync-gdrive --folder "My-Agent-Vault" --credentials service-account.json
gomaa sync-gdrive --daemon --interval 60

# 11. Run standalone Centralized Embedding Microservice
gomaa embed-service --host 0.0.0.0 --port 8000 --model all-MiniLM-L6-v2
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

### 📊 Performance Benchmark Scorecard

Benchmarked on Apple Silicon (M-series) / Ubuntu 24.04 LTS against a live knowledge graph of notes with 384-dimensional vector embeddings:

| Operation | Implementation | Mean Latency | P95 Latency | Throughput |
|---|---|---|---|---|
| **Cold Engine Init** | SQLite WAL + Obsidian Vault | **6.28 ms** | **6.50 ms** | ~160 init/s |
| **Neural Ingest** | FastEmbed ONNX + SQLite + Markdown File IO | **13.50 ms** | **21.47 ms** | ~75 notes/s |
| **Neural Recall** | Query Embedding + Dot Product + Keyword RRF | **13.71 ms** | **14.79 ms** | ~73 queries/s |
| **Keyword FTS Search** | SQLite FTS5 / PostgreSQL GIN `tsvector` | **0.99 ms** | **1.24 ms** | ~1,010 queries/s |
| **Graph Traversal** | Recursive CTE / In-Memory Wikilink Walk | **0.83 ms** | **0.97 ms** | ~1,200 walks/s |
| **Context Assembler** | Top-K Recall + Token Budgeting + XML Packing | **6.12 ms** | **6.45 ms** | ~163 assemblies/s |

### 🔬 Test Suite Coverage (87 / 87 Passed · 100%)

Gomaa maintains a comprehensive automated test suite spanning 27 test modules:

```
collected 87 items
tests/test_adapters.py ..                                                [  2%]
tests/test_assemble_context.py ...                                       [  5%]
tests/test_chunking.py .                                                 [  6%]
tests/test_cli_init.py ..                                                [  9%]
tests/test_compat.py ...                                                 [ 12%]
tests/test_consolidation.py ..                                           [ 14%]
tests/test_embedder.py ...                                               [ 18%]
tests/test_embedder_offline.py .                                         [ 19%]
tests/test_embedder_v32.py ..                                            [ 21%]
tests/test_fts_websearch.py .                                            [ 22%]
tests/test_gdrive_safe_path.py .....                                     [ 28%]
tests/test_gdrive_sync.py ...                                            [ 32%]
tests/test_graph_cycles.py .                                             [ 33%]
tests/test_injection_defense.py ...                                      [ 36%]
tests/test_integration.py ...                                            [ 40%]
tests/test_mcp.py ..                                                     [ 42%]
tests/test_mcp_edge_cases.py ..                                          [ 44%]
tests/test_mcp_server.py ..............                                  [ 60%]
tests/test_reconcile_links.py .                                          [ 62%]
tests/test_remind_me_sqlite.py ....                                      [ 66%]
tests/test_security.py ......                                            [ 73%]
tests/test_security_expanded.py .....                                    [ 79%]
tests/test_shared_memory.py ..                                           [ 81%]
tests/test_sqlite.py .....                                               [ 87%]
tests/test_store_factory.py ...                                          [ 90%]
tests/test_vault.py .....                                                [ 96%]
tests/test_vault_security.py ...                                         [100%]

======================= 87 passed, 33 warnings in 7.05s ========================
```

### 🛠️ How to Execute the Test Suite

```bash
# 1. Run all unit & integration tests locally (Light Mode with SQLite)
uv run pytest tests/ -v

# 2. Run with coverage report
uv run pytest tests/ --cov=mnemosyne --cov-report=term-missing

# 3. Run full test suite including live PostgreSQL + pgvector tests
MEMORY_DB_DSN="postgresql://mnemosyne:mnemosyne@localhost:5432/mnemosyne" uv run pytest tests/ -v
```

### 🛡️ Test Procedure & Hermetic Isolation Principles

1. **Hermetic Test Isolation:** All tests utilize pytest's temporary filesystem fixtures (`tmp_path`) to generate ephemeral Obsidian vaults and SQLite databases, ensuring zero state pollution between runs.
2. **Transaction Rollback Safety:** Database operations and file writes are atomic. If an upsert or vector calculation fails, sibling temporary files (`.note.pid.tmp`) are cleaned up immediately.
3. **Prompt Injection & Red-Teaming Tests:** Automated test suites in [`tests/test_injection_defense.py`](tests/test_injection_defense.py) and [`tests/test_security.py`](tests/test_security.py) continuously verify that LLM control tokens, DAN mode overrides, path traversal attempts, and credential leaks are neutralized.

---

## 📄 License

Apache-2.0 License. Built for the open autonomous agent ecosystem. See [LICENSE](LICENSE) for full details.
