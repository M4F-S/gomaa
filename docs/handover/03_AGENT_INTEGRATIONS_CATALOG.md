# Agent Integrations Catalog 🔌

Mnemosyne can be plugged into any agent framework in under 2 minutes.

---

## 1. OpenClaw
In `openclaw-config.yaml`:
```yaml
plugins:
  mcp_servers:
    mnemosyne:
      command: "python3"
      args: ["-m", "mnemosyne", "server"]
      env:
        MEMORY_DB_DSN: "postgresql://user:password@localhost:5432/openclaw_memory"
        MEMORY_VAULT_PATH: "~/.openclaw/vault"
        MEMORY_DEFAULT_WING: "openclaw"
```

---

## 2. Hermes Framework
In `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  obsidian_memory:
    command: /opt/data/mcp-servers/venv/bin/python
    args:
      - /opt/data/mcp-servers/obsidian_memory_mcp.py
    env:
      MEMORY_DB_DSN: postgresql://mnemosyne:mnemosyne@172.16.8.2:5432/toy_db
      MEMORY_VAULT_PATH: /root/.hermes/vault
```

---

## 3. Claude Desktop
`~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python3",
      "args": ["-m", "mnemosyne", "server"],
      "env": {
        "MEMORY_VAULT_PATH": "~/Documents/Obsidian/ClaudeVault",
        "MEMORY_DEFAULT_WING": "claude"
      }
    }
  }
}
```

---

## 4. Cursor IDE
`.cursor/mcp.json`:
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

---

## 5. Open-Manus, CrewAI & LangChain (Python SDK)
```python
from mnemosyne import UnifiedMemorySystem

mem = UnifiedMemorySystem(vault_path="~/.agent/vault")

# Remember note with domain scoping
mem.remember(
    title="Infrastructure Decision",
    content="Use Docker bridge network 172.16.8.0/24 for PostgreSQL inter-container traffic.",
    wing="devops",
    room="networking",
    tags=["infra", "docker"],
    pinned=True
)

# Recall
results = mem.recall("Docker network", mode="hybrid", scope={"wing": "devops"})
```
