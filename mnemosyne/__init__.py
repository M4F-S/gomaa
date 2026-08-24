"""Mnemosyne v3.0 - Local-first memory system for AI agents."""

import logging

__version__ = "3.0.0"

from mnemosyne.core import UnifiedMemorySystem
from mnemosyne.mcp_server import MCPServer

__all__ = ["UnifiedMemorySystem", "MCPServer", "__version__"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MemoryMCPServer = MCPServer
