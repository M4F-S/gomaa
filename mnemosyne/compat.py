"""Backward-compatible functions (from v1.0)."""

from typing import List, Optional

from mnemosyne.core import UnifiedMemorySystem


_global_memory: Optional[UnifiedMemorySystem] = None


def _get_memory() -> UnifiedMemorySystem:
    global _global_memory
    if _global_memory is None:
        _global_memory = UnifiedMemorySystem(auto_sync=False)
    return _global_memory


def create_note(title: str, content: str, tags=None, note_type="concept", links=None):
    """v1.0 compatible: Create a note."""
    return _get_memory().remember(title, content, tags or [], note_type, links or [])


def read_note(title: str) -> Optional[str]:
    """v1.0 compatible: Read a note."""
    result = _get_memory().vault.read_note(title)
    return result["raw"] if result else None


def search_notes(query: str):
    """v1.0 compatible: Search notes."""
    return _get_memory().recall(query, mode="keyword")


def update_note(title: str, new_content=None, append_content=None, **kwargs):
    """v1.0 compatible: Update a note."""
    mem = _get_memory()
    existing = mem.vault.read_note(title)
    if not existing:
        return None
    if new_content:
        content = new_content
    elif append_content:
        content = existing["body"] + "\n\n" + append_content
    else:
        content = existing["body"]
    fm = existing["frontmatter"]
    return mem.remember(
        title=title,
        content=content,
        tags=fm.get("tags", []),
        note_type=fm.get("type", "concept"),
        links=fm.get("links", []),
    )


def create_moc(title: str, description: str, related_notes: List[str]):
    """v1.0 compatible: Create a Map of Content."""
    content = f"{description}\n\n## Overview\n\n"
    for note in related_notes:
        content += f"- [[{note}]]\n"
    return _get_memory().remember(title, content, ["MOC", "index"], "MOC", related_notes)
