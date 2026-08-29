from gomaa.core import UnifiedMemorySystem
from gomaa.mcp_server import MCPServer


class TestAssembleContext:
    def test_assemble_context_basic(self, tmp_path):
        db_path = f"sqlite://{tmp_path / 'ctx_test.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

        # Store test notes
        mem.remember("Database Config", "PostgreSQL running on port 5432 with pgvector.", tags=["db", "infra"], salience=0.9)
        mem.remember("Redis Config", "Redis cache running on port 6379.", tags=["cache", "infra"], salience=0.7)

        res = mem.assemble_context(query="Database port", max_tokens=1000)

        assert "context_text" in res
        assert "<memory_context>" in res["context_text"]
        assert "</memory_context>" in res["context_text"]
        assert "Database Config" in res["context_text"]
        assert res["notes_included"] >= 1
        assert res["estimated_tokens"] > 0
        assert res["max_tokens"] == 1000

    def test_assemble_context_budget_limit(self, tmp_path):
        db_path = f"sqlite://{tmp_path / 'budget_test.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

        # Store a huge note and small note
        mem.remember("Note 1", "Alpha " * 200, tags=["test"], salience=0.9)
        mem.remember("Note 2", "Beta " * 200, tags=["test"], salience=0.8)

        # Restrict max_tokens to very small
        res = mem.assemble_context(query="Alpha Beta", max_tokens=50)
        assert res["notes_included"] == 1
        assert res["estimated_tokens"] <= 500

    def test_mcp_assemble_context_tool(self, tmp_path):
        db_path = f"sqlite://{tmp_path / 'mcp_ctx.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)
        mem.remember("Server Setup", "NGINX reverse proxy with SSL certificate.", tags=["web"])

        server = MCPServer(memory=mem)
        tools = server._get_tools()
        tool_names = [t["name"] for t in tools]
        assert "memory_assemble_context" in tool_names

        res = server._call_tool("memory_assemble_context", {"query": "NGINX SSL", "max_tokens": 500})
        assert "context_text" in res
        assert "Server Setup" in res["context_text"]
