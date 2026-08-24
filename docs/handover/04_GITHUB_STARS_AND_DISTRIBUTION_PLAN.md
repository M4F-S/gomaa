# GitHub Stars & Multi-Channel Distribution Plan ⭐

**Goal:** Accelerate adoption of `M4F-S/mnemosyne` to 500+ GitHub stars and position it as the standard open memory layer for AI agents.

---

## 1. Distribution Channels & Status

| Channel | Format | Status | Next Actions |
|---|---|---|---|
| **Hacker News** | Show HN Post (`Show HN: Mnemosyne...`) | Submitted (Account `mfathy7`) | Monitor comments, reply with benchmarks & architecture depth |
| **Twitter / X** | 5-Tweet Technical Thread | Posted (Free tier <280 char) | Tag `@AnthropicAI`, `@nousresearch`, `@OpenClawAI`, reply to AI agent launch threads |
| **Awesome-MCP** | Pull Request #12720 | PR Open on `punkpeye/awesome-mcp-servers` | Monitor CI checks & merge notification |
| **Reddit** | `r/ClaudeAI`, `r/Cursor`, `r/selfhosted`, `r/LocalLLaMA` | Ready to post | Post tailored technical walk-throughs (see templates below) |
| **Discord Communities** | Nous Research, Open-Manus, MCP Community | Ready to post | Share in `#tools-and-showcase` and `#mcp-dev` |

---

## 2. Reddit Post Template (for `r/ClaudeAI` & `r/Cursor`)

**Title:** *I built an open-source MCP memory engine that syncs your agent's knowledge directly into an Obsidian markdown vault (with pgvector hybrid search)*

**Body:**
> Hey everyone!
> 
> One of the biggest limitations when using Claude Desktop, Cursor, or autonomous agents for complex projects is **memory loss across sessions**.
>
> I built **Mnemosyne** — an open-source, local-first memory engine for AI agents:
> 
> 🧠 **What it does:**
> 1. **Obsidian Vault Sync:** Every memory your agent stores is written as human-readable Markdown with YAML tags and `[[Wikilinks]]`. You can open your Obsidian vault and visualize your agent's mind in graph view.
> 2. **Hybrid RRF Search:** Combines dense vectors (`all-MiniLM-L6-v2`) with PostgreSQL full-text search (`tsvector`) and recursive graph crawling.
> 3. **Hierarchical Wing & Room Scoping:** Keeps project knowledge partitioned so client A's code never contaminates client B's memory.
> 4. **Ebbinghaus Temporal Decay:** Idle thoughts decay over time, but critical decisions marked `pinned=True` stay permanent.
> 5. **Zero-Setup SQLite Fallback:** Runs locally with zero dependencies if you don't want PostgreSQL.
>
> 📦 **Repo & Docs:** https://github.com/M4F-S/mnemosyne
> 💻 **Install:** `pip install mnemosyne-memory`
> 
> Would love your feedback, PRs, and thoughts on what agent integrations you'd like to see next!

---

## 3. Growth & Star Acceleration Strategy

1. **Submit to Model Context Protocol Directory:** Ensure Mnemosyne is indexed on `mcp.so`, `glama.ai/mcp/servers`, and `smithery.ai`.
2. **Interactive Demo Video / GIF:** Record a 30-second screen recording showing Claude Desktop remembering a fact, searching it via hybrid RRF, and viewing the generated `.md` note with graph connections inside Obsidian.
3. **Write a Technical Blog / Substack / Dev.to Article:** *"Why Vector Databases Alone Aren't Enough for Agent Memory (And How Hybrid RRF + Obsidian Solves It)"*.
