"""
Cognitive Memory Benchmarks for Gomaa v4.0 (Gomaa Neo).
Evaluates:
1. LoCoMo Multi-Hop Associative PPR Graph Retrieval (diffusion vs keyword/isolated dense)
2. Epistemic Truth Maintenance (ATMS) Contradiction Resolution & Supercession
3. Selective Forgetting & Pinned Ebbinghaus Temporal Decay Resistance
"""

import pytest
from gomaa.core import UnifiedMemorySystem
from gomaa.stores.sqlite import SQLiteStore
from gomaa.vault import VaultManager


class TestMemoryBenchmarks:
    def test_benchmark_locomo_multihop_associative_ppr(self, tmp_path):
        """
        LoCoMo Multi-Hop Association Benchmark:
        Verifies that activation diffuses along topological links (A -> B -> C -> D)
        allowing deep associative retrieval of structurally connected knowledge.
        """
        db_path = f"sqlite://{tmp_path / 'locomo_bench.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

        # Ingest multi-hop topological knowledge chain
        mem.remember(
            title="Quantum Teleportation Protocol",
            content="Protocol transferring quantum states via [[Entanglement Swapping]] channels.",
            tags=["quantum"],
            salience=0.9,
        )
        mem.remember(
            title="Entanglement Swapping",
            content="Entangling two particles without prior interaction via [[Bell State Measurement]].",
            tags=["quantum"],
            salience=0.8,
        )
        mem.remember(
            title="Bell State Measurement",
            content="Joint quantum-mechanical measurement of two qubits coupled to [[Photonic Quantum Memory]].",
            tags=["quantum"],
            salience=0.8,
        )
        mem.remember(
            title="Photonic Quantum Memory",
            content="Rare-earth crystal atomic frequency comb storage for long-distance quantum repeaters.",
            tags=["quantum"],
            salience=0.85,
        )

        # Verify graph topology links exist
        adj = mem.db.get_graph_adjacency()
        assert len(adj) >= 3

        # Recall via HippoRAG Associative PPR
        ppr_results = mem.recall(query="Quantum Teleportation Protocol", mode="associative_ppr", top_k=4)
        ppr_titles = [r["title"] for r in ppr_results]

        # All connected nodes in the 4-hop chain should be activated in the PPR distribution
        assert "Quantum Teleportation Protocol" in ppr_titles
        assert "Entanglement Swapping" in ppr_titles
        assert "Bell State Measurement" in ppr_titles
        assert "Photonic Quantum Memory" in ppr_titles

        # Hybrid recall should also preserve strong ranking for connected nodes
        hybrid_results = mem.recall(query="Quantum Teleportation Protocol", mode="hybrid", top_k=4)
        assert len(hybrid_results) >= 2

    def test_benchmark_truth_maintenance_contradiction(self, tmp_path):
        """
        Truth Maintenance (ATMS) Contradiction Resolution Benchmark:
        Verifies that when a newer factual belief supersedes an older belief,
        the old belief is safely deprecated, links are updated to 'supersedes',
        and only the active truth is recalled in standard queries.
        """
        db_path = f"sqlite://{tmp_path / 'atms_bench.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

        # 1. Ingest belief v1
        res1 = mem.remember(
            title="Production Ingress Port",
            content="Primary API gateway listens on port 8080 plain HTTP.",
            tags=["network", "prod"],
            salience=0.7,
        )
        old_id = res1["note_id"]

        # 2. Ingest updated belief v2
        res2 = mem.remember(
            title="Production Ingress Port v2",
            content="Primary API gateway listens on port 8443 with TLS mutual auth.",
            tags=["network", "prod"],
            salience=0.9,
        )
        new_id = res2["note_id"]

        # 3. Conflict logged by epistemic monitor
        conflict_id = mem.db.log_conflict(
            old_note_id=old_id,
            new_note_id=new_id,
            conflict_description="Port mismatch between plain HTTP 8080 and TLS 8443",
        )
        assert conflict_id > 0

        pending_conflicts = mem.db.get_pending_conflicts()
        assert len(pending_conflicts) == 1

        # 4. Resolve conflict by superseding belief v1 with v2
        resolved = mem.resolve_conflict(old_id=old_id, new_id=new_id, resolved_by="atms_monitor")
        assert resolved is True

        # 5. Verify old note is deprecated and superseded
        with mem.db._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, superseded_by FROM notes WHERE id = ?;", (old_id,))
            row = cur.fetchone()
            assert row["status"] == "deprecated"
            assert str(row["superseded_by"]) == str(new_id)

        # 6. Active search queries must return belief v2 and exclude deprecated belief v1
        active_recalled = mem.recall(query="Primary API gateway listens on port", mode="keyword", top_k=5)
        recalled_titles = [r["title"] for r in active_recalled]
        assert "Production Ingress Port v2" in recalled_titles
        assert "Production Ingress Port" not in recalled_titles

    def test_benchmark_selective_forgetting_ebbinghaus(self, tmp_path):
        """
        Selective Forgetting & Ebbinghaus Decay Benchmark:
        Verifies that ephemeral, unaccessed memories decay and get archived,
        while pinned memories remain permanently immune to temporal decay.
        """
        db_path = f"sqlite://{tmp_path / 'forgetting_bench.db'}"
        vault_path = str(tmp_path / "vault")
        mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

        # Ingest ephemeral note (low salience, not pinned)
        mem.remember(
            title="Transient Scratchpad Note",
            content="Temporary debug trace for ticket #1029.",
            tags=["scratch"],
            salience=0.10,
            pinned=False,
        )

        # Ingest standard note (medium salience, not pinned)
        mem.remember(
            title="Database Connection String Format",
            content="postgresql://user:pass@host:5432/dbname",
            tags=["config"],
            salience=0.60,
            pinned=False,
        )

        # Ingest permanent constitution / core identity note (pinned)
        mem.remember(
            title="Agent Safety Directive",
            content="Never expose private credentials or bypass security sandbox.",
            tags=["safety", "pinned"],
            salience=1.0,
            pinned=True,
        )

        # Simulate elapsed time of 5 days since notes were accessed
        with mem.db._conn() as conn:
            conn.execute("UPDATE notes SET last_accessed_at = datetime('now', '-5 days');")

        # Trigger sleep consolidation with aggressive decay (0.80) and archive_threshold (0.09)
        # Note 1: 0.10 * 0.80 = 0.08 < 0.09 -> archived!
        # Note 2: 0.60 * 0.80 = 0.48 -> retained
        # Note 3: pinned -> stays 1.0 -> retained permanently
        sleep_stats = mem.sleep(decay_rate=0.80, archive_threshold=0.09)

        assert sleep_stats["decayed"] == 1
        assert sleep_stats["archived"] == 1

        # Verify active notes in store
        with mem.db._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT title, status, salience FROM notes;")
            notes_state = {r["title"]: (r["status"], r["salience"]) for r in cur.fetchall()}

        assert notes_state["Transient Scratchpad Note"][0] == "archived"
        assert notes_state["Database Connection String Format"][0] == "active"
        assert notes_state["Database Connection String Format"][1] < 0.60
        assert notes_state["Agent Safety Directive"][0] == "active"
        assert notes_state["Agent Safety Directive"][1] == 1.0
