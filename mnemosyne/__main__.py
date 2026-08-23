"""Allow running mnemosyne as a module: python -m mnemosyne"""

import sys

from mnemosyne.mcp_server import MCPServer


def main():
    """Entry point for python -m mnemosyne."""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
