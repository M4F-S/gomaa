import pytest
import tempfile
import os
from gomaa.stores.sqlite import SQLiteStore


class TestReconcileLinks:
    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStore(db_path)

    def test_forward_and_realtime_link_resolution(self, store):
        # 1. Create Note A referencing [[Note B]] before Note B exists
        store.upsert_note("Note A", "This note links to [[Note B]] for details.", ["test"], vault_path="/tmp")

        # 2. Now create Note B
        store.upsert_note("Note B", "This is the target note content.", ["test"], vault_path="/tmp")

        # 3. Verify incoming link to Note B was created automatically in real-time ($O(1)$)
        links = store.search_graph("Note A", depth=1)
        assert len(links) >= 1
        assert any(l["title"] == "Note B" for l in links)
