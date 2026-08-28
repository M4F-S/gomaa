import pytest
from gomaa.core import UnifiedMemorySystem
from gomaa.adapters.langchain import MnemosyneMemory
from gomaa.adapters.crewai import MnemosyneMemoryHandler


class TestAdapters:
    def test_langchain_adapter(self, tmp_path):
        db_path = f"sqlite://{tmp_path / 'lc_test.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

        lc_mem = MnemosyneMemory(memory=mem, wing="support", room="tickets")

        # Save turn
        lc_mem.save_context(
            inputs={"input": "How do I reset my password?"},
            outputs={"output": "Navigate to Settings -> Security -> Reset Password."},
        )

        # Load memory variables
        vars_loaded = lc_mem.load_memory_variables({"input": "password reset"})
        assert "history" in vars_loaded
        assert "<memory_context>" in vars_loaded["history"]
        assert "Reset Password" in vars_loaded["history"]

    def test_crewai_adapter(self, tmp_path):
        db_path = f"sqlite://{tmp_path / 'crew_test.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

        handler = MnemosyneMemoryHandler(memory=mem, crew_name="security_swarm")

        # Save finding
        res = handler.save(
            value="Found open port 8080 on staging host 10.0.0.5",
            metadata={"task": "port_scan", "salience": 0.85},
            agent_role="scanner",
        )
        assert res.get("success") is True

        # Search findings
        results = handler.search("open port 8080", limit=3)
        assert len(results) >= 1
        assert "8080" in results[0]["content"]
