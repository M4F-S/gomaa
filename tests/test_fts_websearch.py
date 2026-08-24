import pytest
import os
from mnemosyne.stores import create_store


class TestFTSWebSearch:
    def test_special_characters_no_crash_sqlite(self):
        store = create_store("sqlite:///tmp/test_fts.db")
        store.upsert_note("Punctuation Note", "Text with special keywords symbols", ["test"], vault_path="/tmp")
        res = store.search_keyword("special")
        assert len(res) >= 1
        assert res[0]["title"] == "Punctuation Note"
