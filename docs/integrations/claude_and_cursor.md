# Integrating Mnemosyne with Claude Desktop, Claude Code & Cursor

Mnemosyne is built on the Model Context Protocol (MCP). It can be configured in any MCP client in seconds.

---

## 1. Claude Desktop (`claude_desktop_config.json`)

* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
* **Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mnemosyne": {
      "command": "python3",
      "args": ["-m", "mnemosyne", "server"],
      "env": {
        "MEMORY_DB_DSN": "postgresql://mnemosyne:mnemosyne@localhost:5432/claude_memory",
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
    "mnemosyne": {
      "command": "python3",
      "args": ["-m", "mnemosyne", "server"],
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

Add Mnemosyne to Claude Code CLI directly:

```bash
claude mcp add mnemosyne -- python3 -m mnemosyne server
```
