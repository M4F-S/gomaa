"""Backward-compatible functions (from v1.0)."""

from typing import List, Optional

from mnemosyne.core import UnifiedMemorySystem


_global_memory: Optional[UnifiedMemorySystem] = None


def _get_memory() -> UnifiedMemorySystem:
    global _global_memory
    if _global_memory is None:
        _global_memory = UnifiedMemorySystem(auto_sync=False)
    return _global_memory


def _embed_links(content: str, links: Optional[List[str]] = None) -> str:
    """Render [[wikilinks]] as a trailing Links section without corrupting content."""
    if not links:
        return content
    link_str = " ".join(
        [f"[[{l}]]" if not l.startswith("[[") else l for l in links]
    )
    return f"{content}\n\nLinks: {link_str}"


def create_note(
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    note_type: str = "concept",
    links: Optional[List[str]] = None,
    wing: str = "general",
    room: str = "general",
    **kwargs,
):
    """v1-v2 backward-compatible wrapper for UnifiedMemorySystem.remember."""
    formatted_content = _embed_links(content, links)
    return _get_memory().remember(
        title=title,
        content=formatted_content,
        tags=tags or [],
        note_type=note_type,
        salience=kwargs.get("salience", 0.5),
        wing=wing,
        room=room,
        pinned=kwargs.get("pinned", False),
    )


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
        salience=kwargs.get("salience", 0.5),
        wing=kwargs.get("wing", "general"),
        room=kwargs.get("room", "general"),
        pinned=kwargs.get("pinned", False),
    )


def create_moc(
    title: str,
    description: str,
    related_notes: List[str],
    wing: str = "general",
    room: str = "general",
    **kwargs,
):
    """v1.0 compatible: Create a Map of Content."""
    content = f"{description}\n\n## Overview\n\n"
    for note in related_notes:
        content += f"- [[{note}]]\n"
    return _get_memory().remember(
        title=title,
        content=content,
        tags=["MOC", "index"],
        note_type="MOC",
        salience=kwargs.get("salience", 0.5),
        wing=wing,
        room=room,
        pinned=kwargs.get("pinned", False),
    )