#!/usr/bin/env bash
# ==============================================================================
# 🧠 Gomaa Memory OS — Zero-Config 1-Line Online Installer
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/M4F-S/gomaa/main/install.sh | bash
# ==============================================================================

set -e

# ANSI Color Codes
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

clear 2>/dev/null || true

echo -e "${PURPLE}${BOLD}"
cat << "EOF"
   ██████╗  ██████╗ ███╗   ███╗ █████╗  █████╗ 
  ██╔════╝ ██╔═══██╗████╗ ████║██╔══██╗██╔══██╗
  ██║  ███╗██║   ██║██╔████╔██║███████║███████║
  ██║   ██║██║   ██║██║╚██╔╝██║██╔══██║██╔══██║
  ╚██████╔╝╚██████╔╝██║ ╚═╝ ██║██║  ██║██║  ██║
   ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
EOF
echo -e "${CYAN}   🧠 Autonomous AI Agent Long-Term Memory OS (v3.5.0)${NC}\n"

echo -e "${CYAN}⚡ [1/4] Checking Python environment...${NC}"
if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo -e "${YELLOW}❌ Python 3.9+ is required but was not found. Please install Python first.${NC}"
    exit 1
fi

PY_VER=$($PY_BIN -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "   ✓ Found Python ${GREEN}${PY_VER}${NC}"

echo -e "\n${CYAN}📦 [2/4] Installing Gomaa Memory OS...${NC}"
if command -v uv >/dev/null 2>&1; then
    uv pip install --system --upgrade git+https://github.com/M4F-S/gomaa.git >/dev/null 2>&1 || uv pip install --upgrade git+https://github.com/M4F-S/gomaa.git
elif command -v pipx >/dev/null 2>&1; then
    pipx install --upgrade git+https://github.com/M4F-S/gomaa.git
elif command -v pip3 >/dev/null 2>&1; then
    pip3 install --user --upgrade git+https://github.com/M4F-S/gomaa.git --break-system-packages 2>/dev/null || pip3 install --user --upgrade git+https://github.com/M4F-S/gomaa.git
else
    pip install --user --upgrade git+https://github.com/M4F-S/gomaa.git --break-system-packages 2>/dev/null || pip install --user --upgrade git+https://github.com/M4F-S/gomaa.git
fi
echo -e "   ✓ Gomaa core package installed successfully!"

echo -e "\n${CYAN}🏛️ [3/4] Initializing local Obsidian vault & SQLite database...${NC}"
VAULT_DIR="$HOME/.gomaa/vault"
mkdir -p "$VAULT_DIR/general" "$VAULT_DIR/projects" "$VAULT_DIR/concepts" "$VAULT_DIR/archive" "$VAULT_DIR/sessions"

$PY_BIN -c "
from gomaa.core import UnifiedMemorySystem
mem = UnifiedMemorySystem(vault_path='$VAULT_DIR')
mem.remember(
    title='Welcome to Gomaa',
    content='# Welcome to Gomaa Memory OS\n\nYour local-first hierarchical knowledge graph memory engine is ready.\n\n- [[5 Cognitive Layers]]\n- [[Hybrid Search]]\n- [[Obsidian Vault Sync]]',
    tags=['system', 'init', 'gomaa'],
    wing='general',
    room='welcome',
    pinned=True
)
print('   ✓ Initialized local knowledge vault at $VAULT_DIR')
"

echo -e "\n${CYAN}🤖 [4/4] Generating MCP Agent Configuration...${NC}"
cat << EOF > "$HOME/.gomaa/mcp_snippet.json"
{
  "mcpServers": {
    "gomaa": {
      "command": "$PY_BIN",
      "args": ["-m", "gomaa", "server"],
      "env": {
        "MEMORY_VAULT_PATH": "$VAULT_DIR",
        "MEMORY_DEFAULT_WING": "general"
      }
    }
  }
}
EOF
echo -e "   ✓ Saved drop-in configuration to ${GREEN}~/.gomaa/mcp_snippet.json${NC}"

echo -e "\n${GREEN}${BOLD}🎉 Installation Complete in 5 seconds!${NC}"
echo -e "─────────────────────────────────────────────────────────────────────────────"
echo -e "${BOLD}🚀 Quick Actions:${NC}"
echo -e "  1. Launch Aurora Web Dashboard:  ${CYAN}gomaa dashboard --port 8765${NC}"
echo -e "  2. Store a memory note:          ${CYAN}gomaa remember \"Title\" \"Content\" --tags ai memory${NC}"
echo -e "  3. Search your knowledge:        ${CYAN}gomaa recall \"search query\" --mode hybrid${NC}"
echo -e "  4. Add to Claude Desktop/Cursor: Copy snippet from ${CYAN}~/.gomaa/mcp_snippet.json${NC}"
echo -e "─────────────────────────────────────────────────────────────────────────────\n"
