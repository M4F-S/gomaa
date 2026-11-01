"""A9: forget must not leave a copy the next sync can resurrect."""
import pytest

from gomaa.core import UnifiedMemorySystem

BODY = "A body long enough for the admission controller to accept it."
DIFFERENT = "A completely different body about another subject, still long enough."


@pytest.fixture
def mem(tmp_path):
    return UnifiedMemorySystem(vault_path=str(tmp_path / "vault"), dsn=str(tmp_path / "g.db"),
                               auto_sync=False)


def test_identical_copy_in_another_scope_is_deleted_too(mem):
    mem.remember("Resurrect Me", BODY, wing="alpha", room="r1")
    stored = [r for r in mem.db.list_notes(limit=10) if r["title"] == "Resurrect Me"][0]
    # legacy root-level copy of the same note
    mem.vault.write_note("Resurrect Me", stored["content"], wing="general", room="general")

    res = mem.forget("Resurrect Me", wing="alpha", room="r1")

    assert res["db_deleted"] is True
    assert len(res["files_deleted"]) == 2, f"only {res['files_deleted']} deleted"
    assert res["duplicate_copies"], "duplicate copy not reported"

    mem.sync_vault_to_db()
    rows = [r for r in mem.db.list_notes(limit=50) if r["title"] == "Resurrect Me"]
    assert rows == [], f"note resurrected by sync: {[(r['wing'], r['room']) for r in rows]}"


def test_conflicting_copy_survives_and_is_reported(mem):
    mem.remember("Same Title", BODY, wing="alpha", room="r1")
    mem.vault.write_note("Same Title", DIFFERENT, wing="general", room="general")

    res = mem.forget("Same Title", wing="alpha", room="r1")

    assert res["db_deleted"] is True
    assert res["conflicting_copies"], "conflict not reported"
    assert not res["duplicate_copies"], "a different note was treated as a duplicate"

    # the other note must still exist on disk
    import os
    assert any(os.path.exists(p) for p in res["conflicting_copies"])

    mem.sync_vault_to_db()
    rows = [r for r in mem.db.list_notes(limit=50) if r["title"] == "Same Title"]
    assert len(rows) == 1 and rows[0]["content"].startswith("A completely different"), \
        f"wrong outcome after sync: {rows}"
