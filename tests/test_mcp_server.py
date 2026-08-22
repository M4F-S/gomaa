import pytest
import json
import signal
import time
from unittest.mock import MagicMock, patch
from mnemosyne.mcp_server import MemoryMCPServer


class TestMemoryMCPServer:
    @pytest.fixture
    def server(self):
        mock_memory = MagicMock()
        mock_memory.db = MagicMock()
        mock_memory.db.__class__.__name__ = "PgVectorStore"
        mock_memory.vault = MagicMock()
        mock_memory.vault.vault_path = "/tmp/vault"
        mock_memory.embedder = MagicMock()
        mock_memory.embedder._provider = "sentence-transformers"
        mock_memory.embedder.model_name = "all-MiniLM-L6-v2"
        mock_memory.embedder.dim = 384
        return MemoryMCPServer(memory=mock_memory)

    def test_initialize(self, server):
        req = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
        resp = server._handle(req)
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["id"] == 1

    def test_tools_list(self, server):
        req = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        resp = server._handle(req)
        assert "tools" in resp["result"]
        tool_names = [t["name"] for t in resp["result"]["tools"]]
        assert "memory_remember" in tool_names
        assert "memory_recall" in tool_names
        assert "memory_remind_me" in tool_names
        assert "memory_audit" in tool_names

    def test_tools_call_remember(self, server):
        server.memory.remember.return_value = {"success": True, "note_id": "123"}
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_remember",
                "arguments": {"title": "Test", "content": "test"},
            },
            "id": 3,
        }
        resp = server._handle(req)
        assert resp["result"] is not None
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["success"]

    def test_tools_call_recall(self, server):
        server.memory.recall.return_value = [{"title": "Test", "score": 0.9}]
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_recall",
                "arguments": {"query": "test"},
            },
            "id": 4,
        }
        resp = server._handle(req)
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "results" in content

    def test_tools_call_error(self, server):
        server.memory.remember.side_effect = RuntimeError("DB is down")
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_remember",
                "arguments": {"title": "Test", "content": "test"},
            },
            "id": 5,
        }
        resp = server._handle(req)
        assert "error" in resp
        assert resp["error"]["code"] == -32000
        assert "DB is down" in resp["error"]["message"]
        assert resp["id"] == 5

    def test_health(self, server):
        server.memory.stats.return_value = {"note_count": 0}
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "memory_audit", "arguments": {}},
            "id": 6,
        }
        resp = server._handle(req)
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "health" in content
        assert content["health"]["server"]["status"] == "healthy"
        assert "store" in content["health"]
        assert "embedder" in content["health"]

    def test_request_count(self, server):
        assert server._request_count == 0
        req = {"jsonrpc": "2.0", "method": "initialize", "id": 7}
        server._handle(req)
        assert server._request_count == 1

    def test_error_count(self, server):
        server.memory.remember.side_effect = RuntimeError("fail")
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_remember",
                "arguments": {"title": "T", "content": "c"},
            },
            "id": 8,
        }
        assert server._error_count == 0
        server._handle(req)
        assert server._error_count == 1

    def test_invalid_method(self, server):
        req = {"jsonrpc": "2.0", "method": "invalid/method", "id": 9}
        resp = server._handle(req)
        assert resp["error"]["code"] == -32601
        assert "Method not found" in resp["error"]["message"]
        assert resp["id"] == 9

    def test_health_content(self, server):
        health = server._health()
        assert health["server"]["status"] == "healthy"
        assert health["server"]["uptime_seconds"] >= 0
        assert health["store"]["type"] == "PgVectorStore"
        assert health["embedder"]["provider"] == "sentence-transformers"
        assert health["embedder"]["model"] == "all-MiniLM-L6-v2"
        assert health["embedder"]["dimension"] == 384

    def test_signal_handlers(self, server):
        with patch("signal.signal") as mock_signal:
            server._setup_signal_handlers()
            assert mock_signal.call_count == 2
            calls = [call[0] for call in mock_signal.call_args_list]
            assert signal.SIGTERM in [c[0] for c in calls]
            assert signal.SIGINT in [c[0] for c in calls]

    def test_running_flag(self, server):
        assert server._running is False

    def test_uptime(self, server):
        uptime = server._uptime()
        assert uptime >= 0
        time.sleep(0.01)
        assert server._uptime() > uptime
