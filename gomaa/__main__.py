"""Allow running gomaa as a module: python -m gomaa"""

import sys

from gomaa.mcp_server import MCPServer


def main():
    """Entry point for python -m gomaa."""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
