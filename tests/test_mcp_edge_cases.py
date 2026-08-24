import pytest
from mnemosyne.mcp_server import MCPServer
from mnemosyne.core import UnifiedMemorySystem


class TestMCPEdgeCases:
    def test_handle_non_dict_payload_returns_error(self, tmp_path):
        mem = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)
        server = MCPServer(memory=mem)
        
        # Test array payload
        resp = server._handle(["not", "a", "dict"])
        assert resp["error"]["code"] == -32600
        
        # Test string payload
        resp = server._handle("string payload")
        assert resp["error"]["code"] == -32600

    def test_tool_call_missing_required_arguments_handled(self, tmp_path):
        mem = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)
        server = MCPServer(memory=mem)
        
        # Missing content in memory_remember
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_remember",
                "arguments": {"title": "Only Title"}
            },
            "id": 42
        }
        resp = server._handle(req)
        assert resp.get("result", {}).get("isError") is True
        
        # Missing query in memory_recall
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_recall",
                "arguments": {}
            },
            "id": 43
        }
        resp = server._handle(req)
        assert resp.get("result", {}).get("isError") is True
