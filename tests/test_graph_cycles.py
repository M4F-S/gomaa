import pytest
import tempfile
import os
from gomaa.stores.sqlite import SQLiteStore


class TestGraphCycles:
    def test_circular_link_traversal_terminates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "cycle.db")
            store = SQLiteStore(db_path)

            id_a = store.upsert_note("Node A", "Links to [[Node B]]", ["cycle"], vault_path="/tmp")
            id_b = store.upsert_note("Node B", "Links to [[Node C]]", ["cycle"], vault_path="/tmp")
            id_c = store.upsert_note("Node C", "Links back to [[Node A]]", ["cycle"], vault_path="/tmp")

            store.update_links(id_a, ["Node B"])
            store.update_links(id_b, ["Node C"])
            store.update_links(id_c, ["Node A"])

            # Traversal with depth 3 should terminate cleanly without infinite loop
            results = store.search_graph("Node A", depth=3)
            assert len(results) <= 3
            titles = [r["title"] for r in results]
            assert "Node B" in titles
            assert "Node C" in titles
