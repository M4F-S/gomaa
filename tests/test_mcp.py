import pytest
from mnemosyne.mcp_server import MemoryMCPServer


class TestMCPServer:
    def test_initialize_request(self):
        server = MemoryMCPServer()
        req = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
        resp = server._handle(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1

    def test_tools_list(self):
        server = MemoryMCPServer()
        req = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        resp = server._handle(req)
        assert resp["result"]["tools"] is not None
