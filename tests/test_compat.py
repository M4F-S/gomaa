"""
Test v1.0 backward compatibility module and embed_service exports.
"""

from gomaa.compat import create_note, read_note, search_notes, update_note, create_moc
from gomaa.embed_service import run_service, create_app


def test_compat_create_and_read_note(tmp_path):
    import gomaa.compat as comp
    from gomaa.core import UnifiedMemorySystem

    # Override global memory for isolated test
    comp._global_memory = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)

    res = create_note(
        title="Compat Note",
        content="Compat note content",
        tags=["compat", "legacy"],
        links=["Related Note"]
    )
    assert res.get("success") is True

    raw = read_note("Compat Note")
    assert raw is not None
    assert "Compat note content" in raw
    assert "[[Related Note]]" in raw

    search_res = search_notes("Compat Note")
    assert len(search_res) > 0

    up_res = update_note("Compat Note", append_content="Appended line")
    assert up_res.get("success") is True


def test_compat_create_moc(tmp_path):
    import gomaa.compat as comp
    from gomaa.core import UnifiedMemorySystem

    comp._global_memory = UnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)

    res = create_moc("Project Index", "Map of content description", ["Note A", "Note B"])
    assert res.get("success") is True
    raw = read_note("Project Index")
    assert "[[Note A]]" in raw
    assert "[[Note B]]" in raw


def test_embed_service_callable():
    assert callable(run_service)
    assert callable(create_app)


def test_mnemosyne_legacy_import_compatibility(tmp_path):
    from mnemosyne import UnifiedMemorySystem as LegacyUnifiedMemorySystem
    from mnemosyne.adapters import MnemosyneMemory, MnemosyneMemoryHandler

    mem = LegacyUnifiedMemorySystem(vault_path=str(tmp_path), auto_sync=False)
    res = mem.remember("Legacy Note", "Saved via mnemosyne legacy import", tags=["legacy"])
    assert res.get("success") is True

    lc = MnemosyneMemory(memory=mem)
    assert lc is not None
    crew = MnemosyneMemoryHandler(memory=mem)
    assert crew is not None
