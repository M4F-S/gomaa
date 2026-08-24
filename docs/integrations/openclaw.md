# Integrating Mnemosyne with OpenClaw

[OpenClaw](https://github.com/openclaw/openclaw) is an open-source, self-hosted autonomous AI agent framework designed for 24/7 multi-channel operation (Discord, Telegram, Slack, WhatsApp, Signal).

By connecting Mnemosyne to OpenClaw, your agent gains persistent hierarchical memory, cross-session recall, semantic search over markdown notes, and Ebbinghaus temporal decay.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                   OpenClaw Agent                       │
│  (Discord / Telegram / Slack / Webhooks / Multi-Modal) │
└───────────────────────────┬────────────────────────────┘
                            │ MCP stdio / Tool Call
                            ▼
┌────────────────────────────────────────────────────────┐
│             Mnemosyne MCP Memory Engine                │
│    (Semantic Search + Graph Crawl + Obsidian Vault)    │
└───────────────────────────┬────────────────────────────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
    ┌──────────────────────┐  ┌──────────────────────┐
    │  PostgreSQL/pgvector │  │ Obsidian .md Vault   │
    │  (or SQLite fallback)│  │ (Human-readable ZK)  │
    └──────────────────────┘  └──────────────────────┘
```

---

## Setup Methods

### Method 1: OpenClaw MCP Configuration (Recommended)

In your OpenClaw agent configuration (`config.yaml` or `openclaw.json`), add the `mnemosyne` MCP server:

```yaml
# openclaw-config.yaml
plugins:
  mcp_servers:
    mnemosyne:
      command: "python3"
      args:
        - "-m"
        - "mnemosyne"
        - "server"
      env:
        MEMORY_DB_DSN: "postgresql://user:password@localhost:5432/openclaw_memory"
        MEMORY_VAULT_PATH: "~/.openclaw/vault"
        MEMORY_DEFAULT_WING: "openclaw"
```

If running without PostgreSQL, Mnemosyne automatically falls back to local SQLite with zero configuration:
```yaml
plugins:
  mcp_servers:
    mnemosyne:
      command: "python3"
      args:
        - "-m"
        - "mnemosyne"
        - "server"
      env:
        MEMORY_VAULT_PATH: "~/.openclaw/vault"
```

---

### Method 2: OpenClaw Python Plugin / Tool Adapter

If you are extending OpenClaw with custom Python hooks or event handlers, use the direct Python SDK:

```python
from openclaw.plugins import BasePlugin, hook
from mnemosyne import UnifiedMemorySystem

class MnemosyneMemoryPlugin(BasePlugin):
    name = "mnemosyne_memory"

    def __init__(self, config):
        super().__init__(config)
        self.memory = UnifiedMemorySystem(
            vault_path=config.get("vault_path", "~/.openclaw/vault"),
            dsn=config.get("db_dsn"),
        )

    @hook("on_message_received")
    def inject_relevant_context(self, context, message):
        """Retrieve relevant past context before the agent formulates its response."""
        relevant_memories = self.memory.recall(
            query=message.text,
            top_k=3,
            mode="hybrid",
            scope={"wing": "openclaw", "room": message.channel_id}
        )
        if relevant_memories:
            context["agent_system_context"] += "\n\n### Relevant Past Knowledge:\n"
            for mem in relevant_memories:
                context["agent_system_context"] += f"- **{mem['title']}**: {mem['content']}\n"

    @hook("on_conversation_turn_complete")
    def persist_important_knowledge(self, user_msg, assistant_msg, metadata):
        """Store key facts or full turn transcripts."""
        if metadata.get("save_memory"):
            self.memory.remember(
                title=f"Chat Context: {user_msg.text[:40]}",
                content=f"**User**: {user_msg.text}\n**Agent**: {assistant_msg.text}",
                tags=["chat", "interaction"],
                wing="openclaw",
                room=metadata.get("channel_id", "general")
            )
```

---

## Available MCP Tools in OpenClaw

| Tool Name | Parameters | Purpose |
|---|---|---|
| `memory_remember` | `title`, `content`, `tags`, `wing`, `room`, `salience` | Stores a structured note with semantic vector embedding & markdown file |
| `memory_recall` | `query`, `mode` (hybrid/semantic/keyword/graph), `scope`, `top_k` | Retrieves relevant notes with RRF hybrid ranking |
| `memory_ingest_session` | `transcript`, `wing`, `room` | Automatically chunks and stores full chat transcripts along turn boundaries |
| `memory_timeline` | `limit` | Returns a chronological log of all recent agent memory operations |
| `memory_history` | `title`, `limit` | Returns past version snapshots of an evolving note |
| `memory_remind_me` | `title`, `content`, `trigger_at`, `recurring` | Sets prospective memory reminders |
| `memory_audit` | *(none)* | Returns system statistics, note counts, active wings, and health metrics |
