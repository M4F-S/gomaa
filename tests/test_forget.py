"""Forget must delete both halves of a memory, or sync brings it back."""
import pytest

from gomaa.core import UnifiedMemorySystem

# Admission control rejects bodies under 10 chars; keep test payloads realistic.
BODY = "Test memory body that is long enough to pass the admission controller."


@pytest.fixture
def mem(tmp_path):
    return UnifiedMemorySystem(vault_path=str(tmp_path / "vault"), dsn=str(tmp_path / "gomaa.db"))


def _files(mem):
    return list(mem.vault.vault_path.rglob("*.md"))


def test_forget_removes_row_and_file(mem):
    mem.remember("Forget me", BODY, wing="operations", room="testing")
    assert _files(mem), "note should have been written to the vault"

    res = mem.forget("Forget me", wing="operations", room="testing")

    assert res["db_deleted"] is True
    assert res["files_deleted"], "vault file must be deleted too"
    assert _files(mem) == []
    assert mem.stats().get("notes", 0) == 0


def test_forget_is_idempotent(mem):
    mem.remember("Twice", BODY, wing="operations", room="testing")
    assert mem.forget("Twice", wing="operations", room="testing")["db_deleted"] is True
    second = mem.forget("Twice", wing="operations", room="testing")
    assert second["db_deleted"] is False
    assert second["files_deleted"] == []


def test_forget_leaves_other_scopes_alone(mem):
    """The whole point of the scope key: same title, two scopes, one deletion."""
    mem.remember("Shared name", BODY, wing="alpha", room="r1")
    mem.remember("Shared name", BODY, wing="beta", room="r1")

    res = mem.forget("Shared name", wing="alpha", room="r1")

    assert res["db_deleted"] is True
    remaining = mem.recall("Shared name", top_k=10)
    hits = [r for r in non_empty(remaining) if r.get("title") == "Shared name"]
    assert len(hits) == 1
    assert hits[0]["wing"] == "beta"


def test_sync_does_not_resurrect_a_forgotten_note(mem):
    mem.remember("Gone for good", BODY, wing="operations", room="testing")
    mem.forget("Gone for good", wing="operations", room="testing")

    assert mem.sync_vault_to_db()["synced"] == 0
    assert mem.stats().get("notes", 0) == 0


def test_keep_file_deletes_row_only(mem):
    mem.remember("Keep the file", BODY, wing="operations", room="testing")
    res = mem.forget("Keep the file", wing="operations", room="testing", delete_vault_file=False)

    assert res["db_deleted"] is True
    assert res["files_deleted"] == []
    assert _files(mem), "file should survive with --keep-file"


def test_dry_run_changes_nothing(mem):
    mem.remember("Dry", BODY, wing="operations", room="testing")
    res = mem.forget("Dry", wing="operations", room="testing", dry_run=True)

    assert res["dry_run"] is True
    assert res["db_deleted"] is False
    assert res["db_row_found"] is True
    assert mem.stats().get("notes", 0) == 1
    assert _files(mem)


def non_empty(result):
    """recall() returns a dict on some paths, a list on others."""
    if isinstance(result, dict):
        return result.get("results") or result.get("notes") or []
    return result or []
