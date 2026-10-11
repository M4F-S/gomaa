import pytest
from gomaa.consolidation import ConsolidationEngine
from gomaa.stores.sqlite import SQLiteStore
from gomaa.vault import VaultManager
from gomaa.embedder import Embedder


class TestDreamConsolidation:
    @pytest.fixture
    def test_env(self, tmp_path):
        db_path = str(tmp_path / "private.db")
        shared_db_path = str(tmp_path / "shared.db")
        vault_path = str(tmp_path / "vault")

        private_store = SQLiteStore(db_path)
        shared_store = SQLiteStore(shared_db_path)
        vault = VaultManager(vault_path)
        embedder = Embedder()

        engine = ConsolidationEngine(
            db=private_store,
            vault=vault,
            embedder=embedder,
            shared_db=shared_store,
        )
        return {
            "private": private_store,
            "shared": shared_store,
            "vault": vault,
            "embedder": embedder,
            "engine": engine,
        }

    def test_sws_crystallization_and_playbook_extraction(self, test_env):
        store = test_env["private"]
        engine = test_env["engine"]

        # Log episodic events:
        # 1. Normal turn
        store.log_event(
            session_id="sess-001",
            event_type="dialogue",
            stimulus="What is the weather today?",
            response="It is sunny and 22 degrees Celsius.",
            surprise_factor=0.1,
            outcome_status="success",
        )
        # 2. High surprise turn (should crystallize to semantic note)
        store.log_event(
            session_id="sess-001",
            event_type="dialogue",
            stimulus="Discovered unexpected quantum memory bug in cache pipeline",
            response="Fix requires pinning buffer cache before async I/O dispatch.",
            surprise_factor=0.9,
            outcome_status="success",
        )
        # 3. Tool call 1
        store.log_event(
            session_id="sess-001",
            event_type="tool_call",
            stimulus="fetch_metrics()",
            response="cpu_usage=95%, mem_usage=88%",
            tool_name="fetch_metrics",
            tool_args={"target": "all"},
            surprise_factor=0.2,
            outcome_status="success",
        )
        # 4. Tool call 2
        store.log_event(
            session_id="sess-001",
            event_type="tool_call",
            stimulus="optimize_cache(flush=True)",
            response="cache flushed, memory reduced to 42%",
            tool_name="optimize_cache",
            tool_args={"flush": True},
            surprise_factor=0.3,
            outcome_status="success",
        )

        unconsolidated_before = store.get_unconsolidated_events()
        assert len(unconsolidated_before) == 4

        # Run sleep consolidation
        stats = engine.run(decay_factor=0.95, archive_threshold=0.10)

        assert stats["crystallized_episodes"] == 4
        assert stats["synthesized_playbooks"] >= 1

        # Check events marked consolidated
        unconsolidated_after = store.get_unconsolidated_events()
        assert len(unconsolidated_after) == 0

        # Verify semantic note crystallized
        notes = store.search_keyword("quantum memory bug", top_k=5)
        assert len(notes) >= 1
        crystallized_note = notes[0]
        assert "crystallized" in crystallized_note["tags"]
        assert crystallized_note["episodic_parent_hash"] is not None

        # Verify procedural playbook synthesized
        playbooks = store.search_playbooks(limit=5)
        assert len(playbooks) >= 1
        pb = playbooks[0]
        assert "sess-001" in pb["skill_name"]
        assert len(pb["tool_sequence"]) == 2

    def test_rem_swarm_playbook_sharing(self, test_env):
        private_store = test_env["private"]
        shared_store = test_env["shared"]
        engine = test_env["engine"]

        # Insert a high-performing playbook in private store
        private_store.upsert_playbook(
            skill_name="deploy_harden_vps",
            domain="devops",
            description="Automated playbook for hardening VPS firewall and ports",
            preconditions=["root_access", "clean_network"],
            tool_sequence=[{"step": 1, "action": "ufw enable"}],
            error_recovery={"action": "rollback"},
        )
        # Record successful executions so bayesian rate exceeds threshold (0.60)
        private_store.record_playbook_execution("deploy_harden_vps", success=True)
        private_store.record_playbook_execution("deploy_harden_vps", success=True)
        private_store.record_playbook_execution("deploy_harden_vps", success=True)

        # Insert a playbook with credentials (should NOT be shared)
        private_store.upsert_playbook(
            skill_name="leak_keys_danger",
            domain="security",
            description="Playbook with leak: sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz",
            preconditions=[],
            tool_sequence=[],
            error_recovery={},
        )
        private_store.record_playbook_execution("leak_keys_danger", success=True)
        private_store.record_playbook_execution("leak_keys_danger", success=True)
        private_store.record_playbook_execution("leak_keys_danger", success=True)

        stats = engine.run()

        assert stats["shared_playbooks"] >= 1

        # Check shared store has deploy_harden_vps
        shared_pb = shared_store.get_playbook("deploy_harden_vps")
        assert shared_pb is not None
        assert shared_pb["domain"] == "devops"

        # Check shared store does NOT have leak_keys_danger
        leaked_pb = shared_store.get_playbook("leak_keys_danger")
        assert leaked_pb is None

    def test_synaptic_homeostasis_truth_maintenance(self, test_env):
        store = test_env["private"]
        engine = test_env["engine"]

        # Create old note and new note
        old_id = store.upsert_note(
            title="Database Connection Config",
            content="Use port 5432 for Postgres legacy cluster.",
            tags=["config"],
            salience=0.5,
        )
        new_id = store.upsert_note(
            title="Database Connection Config v2",
            content="Use port 5433 for Postgres high-availability cluster.",
            tags=["config"],
            salience=0.8,
        )

        # Log conflict
        store.log_conflict(
            old_note_id=old_id,
            new_note_id=new_id,
            conflict_description="Port mismatch between v1 and v2 config.",
        )

        pending_before = store.get_pending_conflicts()
        assert len(pending_before) == 1

        stats = engine.run()

        assert stats["conflicts_resolved"] == 1

        pending_after = store.get_pending_conflicts()
        assert len(pending_after) == 0

        # Verify old note is marked deprecated and superseded_by new note
        with store._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, superseded_by FROM notes WHERE id = ?;", (old_id,))
            row = cur.fetchone()
            assert row["status"] == "deprecated"
            assert str(row["superseded_by"]) == str(new_id)

    def test_rem_latent_link_discovery(self, test_env):
        store = test_env["private"]
        engine = test_env["engine"]

        # Create two unlinked notes sharing specific domain tags
        store.upsert_note(
            title="Zero-Trust mTLS Mesh",
            content="Service mesh mutual TLS authentication policy.",
            tags=["zerotrust", "mtls", "mesh"],
            salience=0.8,
        )
        store.upsert_note(
            title="Envoy Sidecar Proxy mTLS",
            content="Envoy sidecar enforces strict client certificate validation.",
            tags=["zerotrust", "mtls", "envoy"],
            salience=0.8,
        )

        stats = engine.run()
        assert stats["discovered_links"] >= 1

        adj = store.get_graph_adjacency()
        assert "Zero-Trust mTLS Mesh" in adj
        targets = [edge["target_title"] for edge in adj["Zero-Trust mTLS Mesh"]]
        assert "Envoy Sidecar Proxy mTLS" in targets
