# Gomaa 🧠

[![CI](https://github.com/M4F-S/gomaa/actions/workflows/ci.yml/badge.svg)](https://github.com/M4F-S/gomaa/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/gomaa.svg)](https://pypi.org/project/gomaa/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-green.svg)](https://modelcontextprotocol.io/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Production-grade, local-first hierarchical & neuro-inspired cognitive memory engine for autonomous AI agents (v4.0.0 — "Gomaa Neo").**

Gomaa equips AI agents (Hermes, OpenClaw, Claude Desktop, Cursor, Windsurf, CrewAI, LangChain) with permanent, human-like and transhuman long-term memory. It unites human-readable **Obsidian Markdown Vaults** with high-speed **PostgreSQL + pgvector (HNSW)** or zero-config **SQLite WAL**, powering a **4-Quadrant Cognitive Architecture** (Episodic, Semantic, Procedural, Working Memory), **HippoRAG 2 Personalized PageRank (PPR)** associative retrieval, **3-Phase Biological Sleep Consolidation** (SWS + REM + Synaptic Homeostasis), **ACT-R Base-Level Activation**, hybrid Reciprocal Rank Fusion (RRF) search, Ebbinghaus temporal decay, cross-agent fleet sharing, and asynchronous Google Drive cloud synchronization.

<p align="center">
  <img src="docs/assets/gomaa-editorial-architecture.jpg" alt="Gomaa AI Agent Long-Term Memory Architecture" width="100%" />
</p>

---

## 💡 Why Gomaa?

Most AI memory systems suffer from three fundamental flaws:
1. **Black-Box Vector Blobs:** Memories disappear into opaque vector databases. Humans cannot audit, correct, or curate what the agent learned.
2. **Context Pollution & Flat Storage:** Raw chat logs, factual knowledge, and procedural skills are dumped into a single flat vector index without forgetting mechanisms or cognitive separation.
3. **Multi-Hop Blindness & Domain Cross-Contamination:** Standard vector similarity fails when connecting facts across multiple hops, while un-scoped stores leak context across domains.

**Gomaa v4.0 ("Gomaa Neo") solves this:**
* 🧠 **4-Quadrant Cognitive Architecture:** Explicit separation of **Episodic** (`episodic_events` turn ledger), **Semantic** (`notes` + weighted `links`), **Procedural** (`procedural_playbooks` with Bayesian Laplace utility), and **Working Memory** (`working_memory` bounded by Miller's Law $7 \pm 2$).
* 🕸️ **HippoRAG 2 Associative PPR Retrieval:** Single-step multi-hop retrieval using Personalized PageRank ($K=20, \alpha=0.15$) over bi-directional weighted graph links, fused with dense vectors, BM25 FTS, and **ACT-R base-level activation** ($\ln(1 + \text{access\_count})$).
* 🌙 **3-Phase Biological Sleep Consolidation (`gomaa sleep`):** Slow-Wave Sleep (SWS) crystallizes high-surprise episodes into semantic notes and extracts procedural playbooks; REM sleep shares proven playbooks across the agent fleet and discovers latent tag-bridge links; Synaptic Homeostasis resolves epistemic conflicts via an Assumption-based Truth Maintenance System (ATMS).
* 📖 **Human-in-the-Loop Auditability:** Every semantic memory is a human-readable Markdown note in your Obsidian vault with `[[Wiki Links]]` and YAML frontmatter.
* ⏳ **Ebbinghaus Temporal Decay & Pinned Immunity:** Inactive memories fade exponentially ($Salience \times 0.95^{\Delta t}$) while `#pinned` memories stay permanent.
* 🏛️ **Physical Wing & Room Scoping:** A 2-level taxonomy (`wing` = domain/project, `room` = channel/topic) isolates context strictly.
* 🌐 **Cross-Agent Fleet Memory:** Multi-agent swarms share sanitized global policies and high-utility playbooks through `shared_db` while keeping private databases isolated.

---

## 🚀 Quick Start & Installation

Choose between two straightforward deployment modes depending on your setup:

### ⚡ Option 1: Lightweight Standalone Mode (Zero-Config SQLite WAL)

**Best for:** Standalone agents, individual developer workstations (Claude Desktop, Cursor IDE, Windsurf, CLI tools). Zero external database installation required (<1MB package size).

#### A. 1-Line Online Installer

Run this single command in your terminal to install Gomaa, initialize your local Obsidian vault, and generate ready-to-copy MCP configurations:

```bash
curl -fsSL https://raw.githubusercontent.com/M4F-S/gomaa/main/install.sh | bash
```

#### B. Manual Pip Install

```bash
# 1. Install lightweight core
pip install gomaa

# 2. Initialize local memory vault (~/.gomaa/vault)
gomaa init

# 3. Launch interactive web knowledge graph dashboard
gomaa dashboard
```

#### C. Connect to Claude Desktop or Cursor IDE

Add this MCP block to your agent configuration file:

##### 1. Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "gomaa": {
      "command": "python3",
      "args": ["-m", "gomaa", "server"],
      "env": {
        "MEMORY_VAULT_PATH": "~/.gomaa/vault",
        "MEMORY_DEFAULT_WING": "general"
      }
    }
  }
}
```

##### 2. Cursor IDE (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "gomaa": {
      "command": "python3",
      "args": ["-m", "gomaa", "server"],
      "env": {
        "MEMORY_VAULT_PATH": "~/.gomaa/vault",
        "MEMORY_DEFAULT_WING": "codebase"
      }
    }
  }
}
```

---

### 🌟 Option 2: Full Production Fleet Deployment (PostgreSQL + pgvector)

**Best for:** Multi-agent swarms (Hermes, OpenClaw, CrewAI fleets), production servers, and large-scale vector search requiring HNSW indexing, cross-agent `shared_db`, and centralized embedding services.

#### A. Docker Compose (1-Command Full Stack)

Spin up PostgreSQL 16 with `pgvector`, pre-configured memory databases, and the Gomaa MCP server in 5 seconds:

```bash
git clone https://github.com/M4F-S/gomaa.git
cd gomaa
docker compose up -d
```

#### B. Python Package Installation (Full Features)

```bash
# 1. Install Gomaa with all production extras (pgvector, fastembed, server, gdrive)
pip install "gomaa[all]"

# 2. Configure your PostgreSQL connection strings
export MEMORY_DB_DSN="postgresql://gomaa:gomaa_secure_password@localhost:15432/gomaa"
export MEMORY_SHARED_DSN="postgresql://gomaa:gomaa_secure_password@localhost:15432/shared_db"
export MEMORY_VAULT_PATH="~/.gomaa/vault"

# 3. Launch the visual Web Knowledge Graph Dashboard
gomaa dashboard --port 8765
```

---

## 📑 Table of Contents

- [💡 Why Gomaa?](#-why-gomaa)
- [🚀 Quick Start & Installation](#-quick-start--installation)
- [⚡ Complete Feature Matrix](#-complete-feature-matrix)
- [🏗️ System Architecture](#️-system-architecture)
- [🧠 Deep Dive into Key Capabilities](#-deep-dive-into-key-capabilities)
  - [1. 4-Quadrant Cognitive Architecture (v4.0)](#1-4-quadrant-cognitive-architecture-v40)
  - [2. HippoRAG 2 Personalized PageRank (PPR) & Hybrid RRF Search](#2-hipporag-2-personalized-pagerank-ppr--hybrid-rrf-search)
  - [3. 3-Phase Biological Sleep Consolidation (`gomaa sleep`)](#3-3-phase-biological-sleep-consolidation-gomaa-sleep)
  - [4. Hierarchical Wing & Room Taxonomy](#4-hierarchical-wing--room-taxonomy)
  - [5. Cross-Agent Shared Memory Layer (`shared_db`)](#5-cross-agent-shared-memory-layer-shared_db)
  - [6. Ebbinghaus Temporal Decay, ACT-R Activation & Pinned Immunity](#6-ebbinghaus-temporal-decay-act-r-activation--pinned-immunity)
  - [7. Obsidian Markdown Vault & Bi-Directional Graph](#7-obsidian-markdown-vault--bi-directional-graph)
  - [8. Turn-Aware Verbatim Session Ingestor](#8-turn-aware-verbatim-session-ingestor)
  - [9. Cloud & Local Vault Backup (Google Drive, Local Sync, One-Click Archives)](#9-cloud--local-vault-backup-google-drive-local-sync-one-click-archives)
  - [10. Flexible Embedding Backends (FastEmbed / Microservice / Local)](#10-flexible-embedding-backends-fastembed--microservice--local)
  - [11. Defense-in-Depth Security & Data Integrity](#11-defense-in-depth-security--data-integrity)
- [🛠️ MCP Tool Reference (13 Tools)](#️-mcp-tool-reference-13-tools)
- [🌐 Multi-Agent Fleet Production Architecture](#-multi-agent-fleet-production-architecture)
- [🤖 Agent Framework Integration Recipes](#-agent-framework-integration-recipes)
- [💻 Complete CLI Command Reference](#-complete-cli-command-reference)
- [⚙️ Environment Variables Reference](#️-environment-variables-reference)
- [🧪 Testing & Benchmarks](#-testing--benchmarks)
- [📄 License](#-license)

---

## ⚡ Complete Feature Matrix

| Feature | Description | Benefit |
|---|---|---|
| **🤖 MCP Native (v2024-11-05)** | Standardized stdio JSON-RPC protocol server (13 tools) | Seamless drop-in for Claude, Cursor, Windsurf, Hermes, OpenClaw |
| **🧠 4-Quadrant Cognitive Store** | Dedicated schemas for Episodic, Semantic, Procedural, and Working Memory | Prevents chat logs, factual knowledge, and tool skills from polluting each other |
| **🕸️ HippoRAG 2 Associative PPR** | Personalized PageRank ($K=20, \alpha=0.15$) over bi-directional weighted edges | Solves multi-hop associative queries in a single sub-millisecond retrieval step |
| **🌙 3-Phase Sleep Consolidation** | SWS crystallization + REM swarm playbook synthesis & link discovery + ATMS homeostasis | Automatically distills raw episodes into semantic notes and reusable procedural skills |
| **🔎 High-Recall HNSW Vector Search** | `pgvector` HNSW indexing with `vector_cosine_ops` (`m=16, ef_construction=64`) | Sub-millisecond vector recall without clustering retraining |
| **⚖️ Hybrid RRF + ACT-R Ranking** | Fuses Dense (1.0) + FTS (0.8) + Graph (0.6) + HippoRAG PPR (0.9) + Salience/ACT-R | Captures exact technical keywords, multi-hop graph bridges & frequently accessed facts |
| **🏛️ Wing & Room Scoping** | 2-level taxonomy (`wing` = domain/project, `room` = channel/topic) | Eliminates context window bloating & cross-domain hallucination |
| **🌐 Cross-Agent Shared Memory** | Central `shared_db` queryable across multi-agent fleets with credential screening | Collective fleet intelligence without compromising private databases |
| **☁️ Cloud & Local Vault Backup** | Async Google Drive sync, local cloud drive sync (iCloud, Dropbox) & one-click archives | Sub-millisecond local speed + automated cloud backup & conflict branching |
| **⏳ Ebbinghaus Temporal Decay** | Exponential decay $Salience_t = Salience_0 \times (0.95)^{\Delta t}$ with 90-day auto-archive | Auto-prunes transient noise while keeping active memories sharp |
| **📌 Pinned Memory Immunity** | Permanent immunity to decay via `pinned=True` or `#pinned` tags | Guarantees foundational instructions and core rules never fade |
| **📖 Obsidian Zettelkasten** | Writes human-readable Markdown notes with YAML frontmatter & `[[Wiki Links]]` | Direct visual inspection, editing, and graph visualization in Obsidian |
| **📜 Turn-Aware Ingestor** | 1,500-char sliding-window chunking with 200-char overlap along turn boundaries | Preserves entire conversation history without breaking code blocks |
| **🛡️ Prompt Injection Armor** | Neutralizes control tokens (`<|im_start|>`, `[INST]`) in prose; escapes XML context tags | Prevents memory poisoning and context hijacking attacks |
| **🎨 Native Aurora Dashboard** | Zero-dependency embedded web knowledge graph (`gomaa dashboard`) | Real-time visual memory graph, cognitive distribution charts & live query sandbox |
| **📦 Token-Budgeted Assembler** | Packs top-salience memories into exact LLM prompt budgets with XML escaping | Direct drop-in context injection for LLM system prompts without overflow |
| **🔌 Framework Adapters** | Native integrations for LangChain, LangGraph, and CrewAI (including Procedural recall) | Drop-in multi-agent swarm memory with zero boilerplate |
| **🔄 Zero-Config SQLite Light Mode** | Automatic fallback to local SQLite WAL when PostgreSQL is offline | 5-second setup with 100% feature parity for standalone developer workstations |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Clients["🤖 AI Agents & LLM Clients"]
        Claude["Claude Desktop / Cursor"]
        Hermes["Autonomous Multi-Agent Swarms"]
        Swarm["CrewAI / LangGraph Swarms"]
    end

    subgraph Core["🧠 Gomaa Core Engine (v4.0.0 - Gomaa Neo)"]
        direction TB
        MCP["MCP JSON-RPC Server\n(13 Tools · Stdio)"]
        Security["Admission & Security Guard\n(Credential Regex · Control Token Sanitizer)"]
        RRF["Hybrid RRF + HippoRAG 2 PPR Ranker\nDense(1.0) + PPR(0.9) + FTS(0.8) + Graph(0.6) + ACT-R"]
        Sleep["3-Phase Biological Sleep Engine\n(SWS Crystallization · REM Playbooks · ATMS Homeostasis)"]
        Assembler["Token-Budgeted Context Assembler\n(Structured XML Prompt Enclosure)"]
    end

    subgraph Quadrants["🏛️ 4-Quadrant Cognitive Topology (PostgreSQL 16 pgvector & SQLite WAL)"]
        Episodic[("⚡ Episodic Ledger\nepisodic_events")]
        Semantic[("📖 Semantic Graph\nnotes + weighted links")]
        Procedural[("🛠️ Procedural Store\nprocedural_playbooks")]
        Working[("🎯 Working Memory\nworking_memory (7±2)")]
        Vault["📂 Obsidian Markdown Vault\nYAML Frontmatter · [[Wikilinks]]"]
    end

    subgraph Cloud["☁️ Remote Sync (Optional)"]
        GDrive["Google Drive Cloud Sync\n(MD5 Diffing · Conflict Branching)"]
    end

    Clients -->|MCP stdio / Python SDK| MCP
    MCP --> Security
    Security --> RRF
    Security --> Sleep
    RRF <--> Episodic
    RRF <--> Semantic
    RRF <--> Procedural
    RRF <--> Working
    Semantic <--> Vault
    Sleep --> Episodic
    Sleep --> Semantic
    Sleep --> Procedural
    Assembler --> Clients
    Vault <-->|Async Daemon / Cron| GDrive
```

---

## 🧠 Deep Dive into Key Capabilities

### 1. 4-Quadrant Cognitive Architecture (v4.0)
Inspired by cognitive neuroscience (Tulving, Squire, Anderson's ACT-R), Gomaa v4.0 separates agent memory into four specialized stores across both SQLite and PostgreSQL:
* **Episodic Memory (`episodic_events`):** Autonoetic, append-only turn ledger recording raw agent stimuli, tool invocations, outcomes (`success`, `failure`, `partial`), and a `surprise_factor` ($[0.0, 1.0]$).
* **Semantic Memory (`notes` + `links`):** Noetic, decontextualized factual knowledge stored simultaneously in the Obsidian vault and database with typed, weighted edges (`relation_type`, `edge_weight`), `access_count`, and ATMS provenance (`status`, `superseded_by`).
* **Procedural Memory (`procedural_playbooks`):** Executable skill schemas storing `preconditions`, `tool_sequence`, and `error_recovery` policies ranked by Bayesian Laplace-smoothed success rate:
  $$U_{\text{Bayesian}} = \frac{\text{success\_count} + 1}{\text{invocation\_count} + 2}$$
* **Working Memory (`working_memory`):** Session-scoped scratchpad tracking `active_goal`, `subtask_stack`, `hypotheses`, and an `attention_window` strictly bounded by Miller's Law ($7 \pm 2 \Rightarrow \text{max } 9$ items).

### 2. HippoRAG 2 Personalized PageRank (PPR) & Hybrid RRF Search
Standard vector search fails on exact technical strings (e.g. `CVE-2024-38077`) and multi-hop associative bridges. Gomaa v4.0 implements **HippoRAG 2 Personalized PageRank (`associative_ppr`)** alongside hybrid Reciprocal Rank Fusion:
* **Personalized PageRank (`gomaa/hipporag.py`):** Extracts top anchor nodes via dense cosine similarity to build a sparse personalization reset distribution $p$, then runs 20 power iterations ($\alpha=0.15$) over bi-directional forward and backlink graph edges:
  $$\pi^{(k+1)} = \alpha \cdot p + (1 - \alpha) \cdot M^{\top} \pi^{(k)}$$
* **5-Way Hybrid RRF + ACT-R Fusion:**
  $$\text{RRF Score}(d) = \sum_{m \in \text{modes}} w_m \cdot \frac{1}{k + \text{rank}_m(d)} + 0.2 \cdot \text{Salience}(d) + 0.05 \cdot \ln(1 + \text{access\_count}(d))$$
  Combining Dense Vector ($1.0$), HippoRAG PPR ($0.9$), Full-Text Search ($0.8$), 2-Hop Graph Walk ($0.6$), Salience ($0.2$), and ACT-R Base-Level Activation.

### 3. 3-Phase Biological Sleep Consolidation (`gomaa sleep`)
Instead of simple decay, Gomaa v4.0 implements a 3-phase offline consolidation cycle (`ConsolidationEngine.run()`):
1. **Phase 1 — Slow-Wave Sleep (SWS — Episodic-to-Semantic Crystallization):** Scans unconsolidated `episodic_events`. High-surprise episodes ($\text{surprise\_factor} \ge 0.5$ or failure recovery) are crystallized into permanent Semantic Markdown notes in the Obsidian vault and database, while multi-step successful tool trajectories ($\ge 2$ tool calls) are extracted into `procedural_playbooks`.
2. **Phase 2 — REM Sleep (Associative Synthesis & Swarm Skill Sharing):** Promotes high-utility procedural playbooks ($\text{bayesian\_success\_rate} \ge 0.60$, screened by `AdmissionControl`) to the cross-agent `shared_db` fleet store, and discovers latent `rem_associative` links between unlinked semantic notes sharing domain tags.
3. **Phase 3 — Synaptic Homeostasis & ATMS Truth Maintenance:** Resolves pending contradictions in `epistemic_conflicts` by marking superseded notes `status = 'deprecated'` with `superseded_by` provenance pointers, then applies geometric Ebbinghaus step decay ($S_{t+1} = S_t \times d$).

### 4. Hierarchical Wing & Room Taxonomy
Memory cross-contamination is a major failure mode in multi-agent fleets. Gomaa structures memory as a 2-level physical palace:
* **`wing` (Domain/Project):** Top-level domain boundary (e.g. `ecommerce`, `pentest`, `devops`, `shared`).
* **`room` (Topic/Channel):** Granular topic partition (e.g. `database`, `firewall`, `stripe_api`).

Queries can be scoped tightly to a specific wing or room, preventing marketing prompts from recalling penetration testing findings.

### 5. Cross-Agent Shared Memory Layer (`shared_db`)
In autonomous multi-agent environments, agents maintain isolated private databases (e.g. `agent_orchestrator`, `agent_researcher`, `agent_executor`, etc.) to prevent state corruption. However, collective intelligence requires sharing global policies and verified facts.
* **Publishing:** Using `memory_publish_shared`, vetted notes are published to `shared_db`.
* **Credential Screening:** Content is scanned against strict regex filters for Anthropic keys (`sk-ant-`), Google Gemini keys (`AIza...`), HuggingFace tokens (`hf_...`), OpenAI keys (`sk-proj-...`), AWS access keys (`AKIA...`), Slack tokens (`xox-`), and private keys.
* **Fail-Soft Recall:** When an agent queries memory, `memory_recall` queries both the private store and `shared_db`. If the shared database is temporarily unreachable, it degrades gracefully without interrupting the agent.

### 6. Ebbinghaus Temporal Decay, ACT-R Activation & Pinned Immunity
Memories naturally lose relevance over time while frequently recalled memories grow stronger:
* **ACT-R Dynamic Access Tracking:** Every high-confidence semantic or keyword recall increments `access_count` and updates `last_accessed_at`, boosting the note's base-level activation $\ln(1 + \text{access\_count})$.
* **Nightly Auto-Archiving:** Consolidation automatically transitions notes below the archive threshold and unaccessed for $>90\text{ days}$ to `status = 'archived'`.
* **Pinned Immunity:** System rules, core policies, or notes marked with `pinned=True` or tagged `#pinned` receive permanent immunity from temporal decay ($\text{Salience} = 1.0$).

### 7. Obsidian Markdown Vault & Bi-Directional Graph
Every memory created by an agent is simultaneously written as a human-readable `.md` file inside your Obsidian vault:
* **Zettelkasten Frontmatter:** Contains `title`, `date`, `tags`, `type`, `salience`, `wing`, and `room`.
* **Bi-Directional Knowledge Graph:** Target notes mentioned as `[[Target Note]]` are automatically parsed into bi-directional relationships in PostgreSQL & SQLite, enabling 2-hop traversal and HippoRAG PPR propagation across both forward links and backlinks.
* **Live Inspection:** Open Obsidian on your desktop or mobile device and explore your agent fleet's collective memory in Obsidian's interactive Graph View.

### 8. Turn-Aware Verbatim Session Ingestor
Conversational transcripts often contain crucial nuances lost in lossy summarization. `memory_ingest_session`:
* Splits raw transcripts along turn boundaries (`User:`, `Assistant:`, `### Turn`, `**Human**:`).
* For turns longer than 1,500 characters, applies a **linear sliding window** (1,500 chars with 200-char overlap).
* Chains sequential chunks using `[[Session ... Turn 01 Part 02]]` wikilinks, preserving code blocks, execution traces, and conversational flow.

### 9. Cloud & Local Vault Backup (Google Drive, Local Sync, One-Click Archives)
Ensure your agent vaults and memory stores are permanently preserved, version-controlled, and synchronized across cloud providers or local filesystems:

#### A. Direct Google Drive Asynchronous Synchronization (`gomaa sync-gdrive`)
* **Local-First Zero Latency:** Agents read and write directly to the local vault at SSD speeds (<1ms). Background synchronization interacts with the Google Drive v3 API asynchronously without blocking agent execution.
* **Cryptographic MD5 Verification:** Automatically verifies checksums to prevent redundant uploads or downloads.
* **Conflict Branch Preservation:** If a note is updated on Google Drive and modified locally simultaneously, Gomaa automatically preserves the local note as `NoteName.conflict-YYYYMMDD-HHMMSS.md` before updating, guaranteeing zero data loss.
* **Authentication Options:**
  - **Service Account File:** Pass `--credentials /path/to/service-account.json` or set `export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"`.
  - **Service Account JSON String:** Set `export GDRIVE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'`.
  - **User OAuth2 Token:** Set `export GDRIVE_TOKEN_JSON='{"token": "...", "refresh_token": "..."}'`.
* **Execution Modes:**
  ```bash
  # Single one-off sync pass
  gomaa sync-gdrive --folder "Agent-Vault" --credentials service-account.json

  # Continuous background synchronization daemon (e.g. sync every 5 minutes)
  gomaa sync-gdrive --daemon --interval 300
  ```

#### B. Local Cloud Drive & Desktop Folder Sync (`gomaa sync-folder`)
If you use Google Drive for Desktop, Dropbox, iCloud Drive, OneDrive, or an external backup volume, Gomaa can synchronize directly with the synced desktop folder without requiring cloud API keys or developer console setup:
```bash
# Sync with Google Drive for Desktop
gomaa sync-folder "~/Google Drive/My Drive/GomaaVault"

# Sync with Dropbox or iCloud
gomaa sync-folder "~/Dropbox/GomaaVault"
gomaa sync-folder "~/Library/Mobile Documents/com~apple~CloudDocs/GomaaVault"
```

#### C. Universal One-Click Backup & Restore (`gomaa backup` / `gomaa restore`)
Create atomic, timestamped compressed archives containing your entire Obsidian vault (all markdown notes, wikilinks, attachments) and the SQLite database:
```bash
# Create timestamped tar.gz or zip backup archive
gomaa backup --dest ./backups
gomaa backup --dest ~/Google\ Drive/My\ Drive/Backups --format zip

# Restore vault and database from backup archive
gomaa restore ./backups/gomaa-backup-20261014-120000.tar.gz --dest-vault ~/.gomaa/vault
```

### 10. Flexible Embedding Backends (FastEmbed / Microservice / Local)
Gomaa adapts to any deployment resource budget:
1. **FastEmbed ONNX Runtime (Recommended for Standalone Nodes):** Uses ONNX Runtime C++ execution (~30MB RAM). Zero PyTorch overhead.
2. **Centralized Microservice (`gomaa.embed_service`):** Hosts sentence-transformers in a single dedicated container serving multiple agent containers over HTTP (`MEMORY_EMBED_URL`).
3. **Local SentenceTransformers:** Standalone PyTorch execution (`all-MiniLM-L6-v2`, 384-dimensional).
4. **Deterministic Hash Fallback:** Zero-RAM mathematical vector hash for ultra-constrained environments.

### 11. Defense-in-Depth Security & Data Integrity
* **Path Traversal Immunity:** Dual-resolved canonical path checks (`is_relative_to`) ensure file operations cannot escape the vault root.
* **Thread-Safe Atomic Writes:** Files are written to unique sibling temporary files (`.{name}.{pid}.{uuid}.tmp`) and renamed atomically, preventing thread collisions with automatic fallback for `EXDEV` cross-device volume mounts.
* **DB-Failure Safe Rollback:** If a database upsert fails, existing notes are restored from content backups, preventing data corruption.
* **Control Token Neutralization:** Neutralizes LLM injection tokens (`<|im_start|>`, `<|system|>`, `[INST]`, `<<SYS>>`) in prose while preserving code blocks verbatim.
* **Structured XML Context Enclosure:** Recalled memories are wrapped in `<recalled_memory_context id="..." title="..." source="...">` tags with internal tag escaping, ensuring host LLMs never confuse recalled memories with active system directives.

---

## 🛠️ MCP Tool Reference (13 Tools)

All 13 tools are natively exposed to agents over standard MCP JSON-RPC stdio:

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
Search memories across private and shared fleet databases using `hybrid` RRF, `semantic`, `keyword`, 2-hop `graph`, HippoRAG `associative_ppr`, `procedural` playbooks, or `episodic` turns.
```json
{
  "query": "HNSW index configuration parameters",
  "mode": "associative_ppr",
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
  "content": "Verify that all agent connection pools are refreshed with new credentials.",
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

### 9. `memory_ingest_event`
Log a turn-level experiential episode into the biological episodic ledger (`episodic_events`) with a surprise rating and outcome status.
```json
{
  "session_id": "sess-2026-01",
  "event_type": "tool_call",
  "stimulus": "nmap -p 8080 10.0.0.5",
  "response": "Port 8080 open (Apache Tomcat)",
  "tool_name": "nmap_scan",
  "tool_args": {"port": 8080, "target": "10.0.0.5"},
  "surprise_factor": 0.85,
  "outcome_status": "success"
}
```

### 10. `memory_save_playbook`
Store or update a reusable procedural skill playbook (`procedural_playbooks`) with preconditions, tool sequences, error recovery, and Bayesian Laplace-smoothed utility tracking.
```json
{
  "skill_name": "harden_ssh_daemon",
  "domain": "devops",
  "description": "Disable password auth and root password login in sshd_config",
  "preconditions": ["root_access", "ssh_key_installed"],
  "tool_sequence": [
    {"tool": "edit_config", "args": {"file": "/etc/ssh/sshd_config"}},
    {"tool": "systemctl_reload", "args": {"service": "ssh"}}
  ],
  "error_recovery": {"syntax_error": "sshd -t && restore backup"}
}
```

### 11. `memory_sleep`
Trigger the 3-phase biological sleep consolidation engine (Slow-Wave Sleep crystallization + REM swarm playbook synthesis & latent link discovery + ATMS synaptic homeostasis).
```json
{
  "decay_factor": 0.95,
  "archive_threshold": 0.10
}
```

### 12. `memory_working_buffer`
Manage the Miller's Law ($7 \pm 2$) bounded working memory scratchpad (`get`, `update`, `clear`) for active session goals, subtask stacks, hypotheses, and attention windows.
```json
{
  "action": "update",
  "session_id": "sess-2026-01",
  "agent_role": "lead_researcher",
  "active_goal": "Verify zero-downtime migration",
  "subtask_stack": ["Check replica lag", "Switch PgBouncer pool"],
  "hypotheses": ["Replica lag < 10ms under load"],
  "attention_window": [{"note": "PostgreSQL HNSW Tuning", "salience": 0.9}]
}
```

### 13. `memory_audit`
Get real-time memory health metrics, store backend status, request counts, and active wings.
```json
{}
```

---

## 🌐 Multi-Agent Fleet Production Architecture

In enterprise multi-agent production deployments, Gomaa provides strict database isolation per agent container or worker process on an internal Docker network, paired with a central `shared_db` for collective intelligence and vetted fleet-wide policies:

```
                                  ┌─────────────────────────────────────────┐
                                  │       Production Cloud / Cluster        │
                                  └────────────────────┬────────────────────┘
                                                       │
         ┌───────────────────┬──────────────────┼───────────────────┬──────────────────┐
         ▼                   ▼                  ▼                   ▼                  ▼
┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐┌──────────────────┐
│agent-orchestrator││  agent-research  ││  agent-executor  ││  agent-security  ││ agent-operations │
│  (Coordinator)   ││   (Data/Search)  ││   (Code/Tasks)   ││   (Compliance)   ││     (DevOps)     │
│   Database:      ││   Database:      ││   Database:      ││   Database:      ││   Database:      │
│  orchestrator_db ││   research_db    ││   executor_db    ││   security_db    ││  operations_db   │
└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘└────────┬─────────┘
         │                   │                  │                   │                  │
         └───────────────────┴──────────────────┼───────────────────┴──────────────────┘
                                                │
                                                ▼
                               ┌───────────────────────────────────┐
                               │   PostgreSQL 16 + pgvector (HNSW) │
                               │   - Private Isolated Agent DBs    │
                               │   - Shared Collective DB          │
                               └───────────────────────────────────┘
```

### Architectural Guarantees:
1. **Zero Domain Bleed:** Each agent maintains its own private `pgvector` or `SQLite` database. Queries generated by `agent-security` will never recall unrelated working context from `agent-operations`.
2. **Sanitized Fleet Knowledge Sharing (`shared_db`):** High-utility procedural playbooks and verified domain policies can be published globally using `memory_publish_shared`. Content passes automated regex credential screening (neutralizing API keys, passwords, and private tokens) before reaching the shared layer.
3. **Resilient Fail-Soft Federation:** When an agent invokes `memory_recall(include_shared=True)`, Gomaa queries both the agent's private store and the fleet `shared_db`. If the shared database is temporarily offline or undergoing maintenance, Gomaa gracefully returns private memory results without throwing an exception or interrupting agent execution.

---

## 🤖 Agent Framework Integration Recipes

### 1. Hermes Agent Swarm (`~/.hermes/config.yaml`)
```yaml
mcp_servers:
  obsidian_memory:
    command: python3
    args: ["-m", "gomaa", "server"]
    env:
      MEMORY_AGENT_NAME: "agent-orchestrator"
      MEMORY_DB_DSN: "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/orchestrator_db"
      MEMORY_SHARED_DSN: "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/shared_db"
      MEMORY_VAULT_PATH: "~/.hermes/vault"
```

### 2. OpenClaw (`openclaw-config.yaml`)
```yaml
plugins:
  mcp_servers:
    gomaa:
      command: "python3"
      args: ["-m", "gomaa", "server"]
      env:
        MEMORY_VAULT_PATH: "~/.openclaw/vault"
        MEMORY_DEFAULT_WING: "openclaw"
```

### 3. LangChain & LangGraph
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

### 4. CrewAI Multi-Agent Swarms
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

### 5. Python SDK & Autonomous Agent Scripts
```python
from gomaa import UnifiedMemorySystem

mem = UnifiedMemorySystem(
    vault_path="~/.agent/vault",
    dsn="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/agent_db",
    shared_dsn="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/shared_db"
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
gomaa init --path ~/.gomaa/vault

# 2. Launch interactive Aurora Web Knowledge Graph Dashboard
gomaa dashboard --port 8765

# 3. Store a memory note
gomaa remember "API Architecture" "Uses Bearer JWT auth." --tags security auth --wing backend --room api --salience 0.8 --pinned

# 4. Publish shared fleet memory
gomaa publish-shared "Global Production Policy" "Always check SSL certs." --wing devops

# 5. Search memories (hybrid / semantic / keyword / graph / associative_ppr / procedural / episodic)
gomaa recall "JWT authentication" --mode associative_ppr --top-k 5 --wing backend

# 6. Assemble token-budgeted prompt context block
gomaa assemble-context "production policy" --max-tokens 1500 --wing devops

# 7. View activity timeline
gomaa timeline --limit 20

# 8. Trigger 3-phase biological sleep consolidation (SWS + REM + Homeostasis)
gomaa sleep --decay-rate 0.95 --archive-threshold 0.10

# 9. Trigger Ebbinghaus decay & link reconciliation
gomaa consolidate --decay-rate 0.95 --archive-threshold 0.05

# 10. Check system statistics & health
gomaa stats

# 11. Create a timestamped compressed backup archive (vault + database)
gomaa backup --dest ./backups --format tar.gz

# 12. Restore vault and database from backup archive
gomaa restore ./backups/gomaa-backup-20261014-120000.tar.gz --dest-vault ~/.gomaa/vault

# 13. Sync vault with local cloud folder (Google Drive for Desktop, Dropbox, iCloud)
gomaa sync-folder "~/Google Drive/My Drive/GomaaVault"

# 14. Synchronize with Google Drive API (One-off pass or daemon mode)
gomaa sync-gdrive --folder "My-Agent-Vault" --credentials service-account.json
gomaa sync-gdrive --daemon --interval 300

# 15. Run standalone Centralized Embedding Microservice
gomaa embed-service --host 0.0.0.0 --port 8000 --model all-MiniLM-L6-v2
```

---

## ⚙️ Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `MEMORY_VAULT_PATH` | `~/.gomaa/vault` | Filesystem path to the local Obsidian Markdown vault directory |
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
| **HippoRAG 2 PPR** | 20-Step Power Iteration ($K=20, \alpha=0.15$) | **1.42 ms** | **1.85 ms** | ~700 walks/s |
| **Keyword FTS Search** | SQLite FTS5 / PostgreSQL GIN `tsvector` | **0.99 ms** | **1.24 ms** | ~1,010 queries/s |
| **Graph Traversal** | Recursive CTE / In-Memory Wikilink Walk | **0.83 ms** | **0.97 ms** | ~1,200 walks/s |
| **Context Assembler** | Top-K Recall + Token Budgeting + XML Packing | **6.12 ms** | **6.45 ms** | ~163 assemblies/s |

### 🔬 Test Suite Coverage (126 / 126 Passed · 100%)

Gomaa v4.0 maintains a comprehensive automated test suite spanning 33 test modules (including LoCoMo, LongMemEval, and HotpotQA multi-hop cognitive benchmark harnesses):

```
collected 126 items
tests/benchmarks/test_memory_benchmarks.py ...                           [  2%]
tests/test_adapters.py ..                                                [  3%]
tests/test_assemble_context.py ...                                       [  6%]
tests/test_backup.py ....                                                [  9%]
tests/test_chunking.py .                                                 [ 10%]
tests/test_cli_init.py ..                                                [ 11%]
tests/test_compat.py ....                                                [ 15%]
tests/test_consolidation.py ..                                           [ 16%]
tests/test_dashboard.py ......                                           [ 21%]
tests/test_dream_consolidation.py ....                                   [ 24%]
tests/test_embedder.py ...                                               [ 26%]
tests/test_embedder_offline.py .                                         [ 27%]
tests/test_embedder_v32.py ..                                            [ 29%]
tests/test_fts_websearch.py .                                            [ 30%]
tests/test_gdrive_safe_path.py .....                                     [ 34%]
tests/test_gdrive_sync.py .....                                          [ 38%]
tests/test_graph_cycles.py .                                             [ 38%]
tests/test_hipporag.py ...                                               [ 41%]
tests/test_injection_defense.py ...                                      [ 43%]
tests/test_integration.py ...                                            [ 46%]
tests/test_mcp.py ..                                                     [ 47%]
tests/test_mcp_edge_cases.py ....                                        [ 50%]
tests/test_mcp_server.py ...................                             [ 65%]
tests/test_quadrant_stores.py .......                                    [ 71%]
tests/test_reconcile_links.py .                                          [ 72%]
tests/test_remind_me_sqlite.py ....                                      [ 75%]
tests/test_security.py ......                                            [ 80%]
tests/test_security_expanded.py .....                                    [ 84%]
tests/test_shared_memory.py ..                                           [ 85%]
tests/test_sqlite.py .....                                               [ 89%]
tests/test_store_factory.py ...                                          [ 92%]
tests/test_vault.py .....                                                [ 96%]
tests/test_vault_security.py .....                                       [100%]

======================= 126 passed in 8.12s =======================
```

### 🛠️ How to Execute the Test Suite

```bash
# 1. Run all unit & integration tests locally (Light Mode with SQLite)
uv run pytest tests/ -v

# 2. Run with coverage report
uv run pytest tests/ --cov=gomaa --cov-report=term-missing

# 3. Run full test suite including live PostgreSQL + pgvector tests
MEMORY_DB_DSN="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}" uv run pytest tests/ -v
```

### 🛡️ Test Procedure & Hermetic Isolation Principles

1. **Hermetic Test Isolation:** All tests utilize pytest's temporary filesystem fixtures (`tmp_path`) to generate ephemeral Obsidian vaults and SQLite databases, ensuring zero state pollution between runs.
2. **Transaction Rollback Safety:** Database operations and file writes are atomic. If an upsert or vector calculation fails, sibling temporary files (`.note.pid.tmp`) are cleaned up immediately.
3. **Prompt Injection & Red-Teaming Tests:** Automated test suites in [`tests/test_injection_defense.py`](tests/test_injection_defense.py) and [`tests/test_security.py`](tests/test_security.py) continuously verify that LLM control tokens, DAN mode overrides, path traversal attempts, and credential leaks are neutralized.

---

## 📄 License

Apache-2.0 License. Built for the open autonomous agent ecosystem. See [LICENSE](LICENSE) for full details.
