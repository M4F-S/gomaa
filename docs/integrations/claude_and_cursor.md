# Integrating Gomaa with Claude Desktop, Claude Code & Cursor

Gomaa is built on the Model Context Protocol (MCP). It can be configured in any MCP client in seconds.

---

## 1. Claude Desktop (`claude_desktop_config.json`)

* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
* **Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gomaa": {
      "command": "python3",
      "args": ["-m", "gomaa", "server"],
      "env": {
        "MEMORY_DB_DSN": "postgresql://gomaa:***@localhost:5432/claude_memory",
        "MEMORY_VAULT_PATH": "~/Documents/Obsidian/ClaudeVault",
        "MEMORY_DEFAULT_WING": "personal"
      }
    }
  }
}
```

---

## 2. Cursor IDE (`.cursor/mcp.json`)

In Cursor settings (Features → MCP) or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gomaa": {
      "command": "python3",
      "args": ["-m", "gomaa", "server"],
      "env": {
        "MEMORY_VAULT_PATH": "./.vault",
        "MEMORY_DEFAULT_WING": "my-codebase"
      }
    }
  }
}
```

---

## 3. Claude Code CLI (`~/.claude.json` or `claude mcp add`)

Add Gomaa to Claude Code CLI directly:

```bash
claude mcp add gomaa -- python3 -m gomaa server
```
