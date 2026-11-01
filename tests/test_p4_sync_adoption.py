"""P4: sync must never discard a body when two files share a title."""
import pytest

from gomaa.core import UnifiedMemorySystem

BODY_ALPHA = "Alpha body about the quarterly budget, long enough to pass admission control."
BODY_ROOT = "Root body about something else entirely, distinct text that must survive."


@pytest.fixture
def mem(tmp_path):
    return UnifiedMemorySystem(vault_path=str(tmp_path / "vault"), dsn=str(tmp_path / "g.db"),
                               auto_sync=False)


def _rows(mem):
    return {(r["title"], r["wing"], r["room"]): r["content"] for r in mem.db.list_notes(limit=100)}


def test_distinct_root_file_is_not_merged_into_a_scoped_note(mem):
    mem.remember("Budget", BODY_ALPHA, wing="alpha", room="r1")
    mem.vault.write_note("Budget", BODY_ROOT, wing="general", room="general")

    mem.sync_vault_to_db()
    rows = _rows(mem)

    same_title = {k: v for k, v in rows.items() if k[0] == "Budget"}
    assert len(same_title) == 2, f"two distinct notes collapsed: {same_title}"
    bodies = " ".join(same_title.values())
    assert "quarterly budget" in bodies and "must survive" in bodies, \
        "one of the two bodies was lost"


def test_identical_root_copy_is_adopted_not_duplicated(mem):
    """The case the adoption rule was written for: the same note, indexed once."""
    mem.remember("Deployment Note", "A deployment body long enough to pass admission control.",
                 wing="operations", room="infra")
    stored = [r for r in mem.db.list_notes(limit=10) if r["title"] == "Deployment Note"][0]

    # same body, written at the vault root (where it has no wing/room in its path)
    mem.vault.write_note("Deployment Note", stored["content"], wing="general", room="general")

    mem.sync_vault_to_db()
    rows = [r for r in mem.db.list_notes(limit=50) if r["title"] == "Deployment Note"]
    assert len(rows) == 1, f"identical content duplicated: {[(r['wing'], r['room']) for r in rows]}"
    assert (rows[0]["wing"], rows[0]["room"]) == ("operations", "infra"), "scope not adopted"
