import json
import gomaa
import pytest
from unittest.mock import MagicMock, patch
import signal
import time
from gomaa.mcp_server import MCPServer


class TestMemoryMCPServer:
    @pytest.fixture
    def server(self):
        mock_memory = MagicMock()
        mock_memory.remember.return_value = {"success": True, "note_id": 1}
        mock_memory.recall.return_value = [{"title": "Test", "score": 0.9}]
        mock_memory.stats.return_value = {"notes": 10, "links": 5}
        mock_memory.log_event.return_value = {"id": 1, "session_id": "s1"}
        mock_memory.upsert_playbook.return_value = {"id": 1, "skill_name": "sk1"}
        mock_memory.sleep.return_value = {"reconciled_links": 2, "decayed": 0, "archived": 0, "engine": {}}
        mock_memory.get_working_memory.return_value = {"session_id": "s1", "active_goal": "test"}
        mock_memory.clear_working_memory.return_value = True
        mock_memory.update_working_memory.return_value = {"session_id": "s1", "active_goal": "new"}
        mock_memory.db = MagicMock()
        mock_memory.vault = MagicMock()
        mock_memory.vault.vault_path = "/mock/vault"
        mock_memory.embedder = MagicMock()
        mock_memory.embedder._provider = "test"
        mock_memory.embedder.model_name = "test-model"
        mock_memory.embedder.dim = 384
        mock_memory.embedder.embed_url = None
        mock_memory.shared_db = None
        return MCPServer(memory=mock_memory)

    def test_initialize(self, server):
        req = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
        resp = server._handle(req)
        assert resp["result"]["serverInfo"]["name"] == "gomaa"
        assert resp["result"]["serverInfo"]["version"] == gomaa.__version__
        assert resp["result"]["protocolVersion"] == "2024-11-05"

    def test_tools_list(self, server):
        req = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
        resp = server._handle(req)
        tools = resp["result"]["tools"]
        assert len(tools) == 13
        tool_names = [t["name"] for t in tools]
        assert "memory_remember" in tool_names
        assert "memory_publish_shared" in tool_names
        assert "memory_recall" in tool_names
        assert "memory_assemble_context" in tool_names
        assert "memory_audit" in tool_names
        assert "memory_ingest_event" in tool_names
        assert "memory_save_playbook" in tool_names
        assert "memory_sleep" in tool_names
        assert "memory_working_buffer" in tool_names

    def test_tools_call_remember(self, server):
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_remember",
                "arguments": {"title": "Test", "content": "Content", "tags": ["tag1"]},
            },
            "id": 3,
        }
        resp = server._handle(req)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["success"] is True

    def test_tools_call_recall(self, server):
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "memory_recall", "arguments": {"query": "test query"}},
            "id": 4,
        }
        resp = server._handle(req)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert len(content["results"]) == 1

    def test_tools_call_error(self, server):
        server.memory.remember.side_effect = Exception("Store error")
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_remember",
                "arguments": {"title": "Error", "content": "Content"},
            },
            "id": 5,
        }
        resp = server._handle(req)
        assert resp.get("result", {}).get("isError") is True
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "error" in content

    def test_health(self, server):
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "memory_audit", "arguments": {}},
            "id": 6,
        }
        resp = server._handle(req)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "stats" in content
        assert "health" in content
        assert content["health"]["server"]["status"] == "healthy"

    def test_request_count(self, server):
        initial_requests = server._request_count
        req = {"jsonrpc": "2.0", "method": "ping", "id": 7}
        server._handle(req)
        assert server._request_count == initial_requests + 1

    def test_error_count(self, server):
        initial_errors = server._error_count
        server.memory.remember.side_effect = Exception("Store error")
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_remember",
                "arguments": {"title": "Error", "content": "Content"},
            },
            "id": 7,
        }
        server._handle(req)
        assert server._error_count == initial_errors + 1

    def test_missing_tool(self, server):
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "nonexistent_tool"},
            "id": 8,
        }
        resp = server._handle(req)
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "error" in content

    def test_invalid_method(self, server):
        req = {"jsonrpc": "2.0", "method": "invalid/method", "id": 9}
        resp = server._handle(req)
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_health_content(self, server):
        health = server._health()
        assert health["server"]["status"] == "healthy"
        assert health["server"]["version"] == gomaa.__version__
        assert "store" in health
        assert "embedder" in health

    def test_signal_handlers(self, server):
        with patch("signal.signal") as mock_signal:
            server._setup_signal_handlers()
            assert mock_signal.call_count == 2
            calls = [call[0] for call in mock_signal.call_args_list]
            assert signal.SIGTERM in [c[0] for c in calls]
            assert signal.SIGINT in [c[0] for c in calls]

    def test_running_flag(self, server):
        assert server._running is True
        server._handle_signal(signal.SIGTERM, None)
        assert server._running is False

    def test_uptime(self, server):
        uptime = server._uptime()
        assert uptime >= 0
        time.sleep(0.01)
        assert server._uptime() > uptime

    def test_tools_call_ingest_event(self, server):
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_ingest_event",
                "arguments": {
                    "session_id": "sess-42",
                    "stimulus": "test stimulus",
                    "response": "test response",
                    "surprise_factor": 0.8,
                },
            },
            "id": 10,
        }
        resp = server._handle(req)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["session_id"] == "s1"
        server.memory.log_event.assert_called_once()

    def test_tools_call_save_playbook(self, server):
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_save_playbook",
                "arguments": {
                    "skill_name": "backup_vps",
                    "domain": "devops",
                    "description": "Backup VPS data",
                },
            },
            "id": 11,
        }
        resp = server._handle(req)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["skill_name"] == "sk1"
        server.memory.upsert_playbook.assert_called_once()

    def test_tools_call_sleep(self, server):
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_sleep",
                "arguments": {"decay_factor": 0.90, "archive_threshold": 0.15},
            },
            "id": 12,
        }
        resp = server._handle(req)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "reconciled_links" in content
        server.memory.sleep.assert_called_once_with(decay_rate=0.90, archive_threshold=0.15)

    def test_tools_call_working_buffer(self, server):
        # 1. Update action
        req_update = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_working_buffer",
                "arguments": {
                    "action": "update",
                    "session_id": "sess-wb",
                    "active_goal": "solve bug",
                },
            },
            "id": 13,
        }
        resp_up = server._handle(req_update)
        assert "result" in resp_up
        content_up = json.loads(resp_up["result"]["content"][0]["text"])
        assert content_up["active_goal"] == "new"

        # 2. Get action
        req_get = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_working_buffer",
                "arguments": {"action": "get", "session_id": "sess-wb"},
            },
            "id": 14,
        }
        resp_get = server._handle(req_get)
        assert "result" in resp_get
        content_get = json.loads(resp_get["result"]["content"][0]["text"])
        assert content_get["working_memory"]["active_goal"] == "test"

        # 3. Clear action
        req_clear = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_working_buffer",
                "arguments": {"action": "clear", "session_id": "sess-wb"},
            },
            "id": 15,
        }
        resp_clear = server._handle(req_clear)
        assert "result" in resp_clear
        content_clear = json.loads(resp_clear["result"]["content"][0]["text"])
        assert content_clear["cleared"] is True

    def test_v4_tools_json_string_coercion(self, server):
        # Verify JSON-stringified lists and dicts are coerced properly
        req_pb = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "memory_save_playbook",
                "arguments": {
                    "skill_name": "coerced_skill",
                    "domain": "devops",
                    "description": "Test stringified JSON coercion",
                    "preconditions": '["docker_running", "root_access"]',
                    "tool_sequence": '[{"tool": "docker_ps"}]',
                    "error_recovery": '{"retry": 3}',
                },
            },
            "id": 16,
        }
        resp_pb = server._handle(req_pb)
        assert "result" in resp_pb
        server.memory.upsert_playbook.assert_called_with(
            skill_name="coerced_skill",
            domain="devops",
            description="Test stringified JSON coercion",
            preconditions=["docker_running", "root_access"],
            tool_sequence=[{"tool": "docker_ps"}],
            error_recovery={"retry": 3},
        )
