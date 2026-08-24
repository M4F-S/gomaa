"""
Vault manager for Obsidian-compatible markdown files (v3.3).
Features:
- Strict path traversal prevention with dual resolved paths.
- Atomic file writes via sibling .tmp files with EXDEV fallback.
- Code-block-aware wikilink extraction.
"""

import errno
import logging
import os
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("unified-memory")

VAULT_PATH = os.environ.get(
    "MEMORY_VAULT_PATH", os.path.expanduser("~/.mnemosyne/vault")
)


def safe_filename(title: str) -> str:
    """Convert a title to a safe filename."""
    normalized = unicodedata.normalize("NFKC", title)
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", normalized)
    safe = safe.strip()[:150]
    return safe + ".md" if safe else "untitled.md"


def get_safe_note_path(vault_root: Path, wing: str = "general", room: str = "general", title: str = "note") -> Path:
    """
    Constructs a fully verified, non-traversing path inside the vault root.
    Explicitly raises ValueError on directory traversal attempts.
    """
    for comp_name, comp_val in [("wing", wing), ("room", room), ("title", title)]:
        if ".." in comp_val or "/" in comp_val or "\\" in comp_val:
            raise ValueError(f"Security Alert: Path traversal attempt detected in {comp_name}: {comp_val}")

    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()[:150] or "untitled"
    safe_wing = "".join(c for c in wing if c.isalnum() or c in ('_', '-')).strip() or "general"
    safe_room = "".join(c for c in room if c.isalnum() or c in ('_', '-')).strip() or "general"

    root_resolved = vault_root.resolve()
    target_resolved = (root_resolved / safe_wing / safe_room / f"{safe_title}.md").resolve()

    if not target_resolved.is_relative_to(root_resolved):
        raise ValueError(f"Security Alert: Path traversal attempt detected ({target_resolved})")
    return target_resolved


def _atomic_write_text(target_path: Path, text: str) -> None:
    """
    Atomically write text to target_path using a sibling temporary file.
    Includes fallback for cross-device filesystem moves (EXDEV).
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.parent / f".{target_path.name}.{os.getpid()}.tmp"
    try:
        tmp_path.write_text(text, encoding="utf-8")
        try:
            os.replace(tmp_path, target_path)
        except OSError as e:
            if e.errno == errno.EXDEV:
                shutil.move(str(tmp_path), str(target_path))
            else:
                raise
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


class VaultManager:
    """
    Manages the Obsidian-compatible markdown vault.
    Files are human-readable Markdown with YAML frontmatter.
    """

    def __init__(self, vault_path: str = VAULT_PATH) -> None:
        self.vault_path = Path(os.path.expanduser(str(vault_path)))
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def write_note(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        note_type: str = "concept",
        status: str = "active",
        salience: float = 0.5,
        links: Optional[List[str]] = None,
        wing: str = "general",
        room: str = "general",
    ) -> Path:
        """Write a note atomically to the vault with path traversal protection."""
        tags = tags or []
        links = links or []

        # Enforce path traversal safety
        filepath = get_safe_note_path(self.vault_path, wing=wing, room=room, title=title)

        frontmatter = {
            "title": title,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "tags": tags,
            "type": note_type,
            "status": status,
            "salience": salience,
            "wing": wing,
            "room": room,
            "links": links,
        }

        body = f"# {title}\n\n{content}"
        if links:
            body += "\n\n## Related\n\n"
            for link in links:
                body += f"- [[{link}]]\n"

        import yaml  # type: ignore[import-untyped]

        yaml_content = yaml.dump(
            frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
        full = f"---\n{yaml_content}---\n{body}\n"

        _atomic_write_text(filepath, full)
        return filepath

    def read_note(self, title: str, wing: str = "general", room: str = "general") -> Optional[Dict]:
        """Read a note from the vault."""
        try:
            filepath = get_safe_note_path(self.vault_path, wing=wing, room=room, title=title)
        except ValueError:
            return None

        if not filepath.exists():
            root_fallback = self.vault_path / safe_filename(title)
            if root_fallback.exists():
                filepath = root_fallback
            else:
                return None

        text = filepath.read_text(encoding="utf-8")
        result = self._parse_note(text)
        result["title"] = result["frontmatter"].get("title", title)
        body = result["body"]
        heading = f"# {title}\n\n"
        if body.startswith(heading):
            result["content"] = body[len(heading):]
        else:
            result["content"] = body
        return result

    def _parse_note(self, text: str) -> Dict:
        """Parse markdown with YAML frontmatter."""
        import yaml  # type: ignore[import-untyped]

        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except Exception:
                    frontmatter = {}
                body = parts[2].strip()
                return {"frontmatter": frontmatter, "body": body, "raw": text}
        return {"frontmatter": {}, "body": text, "raw": text}

    def extract_wiki_links(self, text: str) -> List[str]:
        """
        Extract canonical target note titles from [[Wiki Links]],
        ignoring code blocks, section headers (#section), and aliases (|alias).
        """
        if not text:
            return []

        clean_text = re.sub(r"```[\s\S]*?```", "", text)
        clean_text = re.sub(r"`[^`]*?`", "", clean_text)
        matches = re.findall(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]", clean_text)

        seen = set()
        result = []
        for m in matches:
            target = m.strip()
            if target and target not in seen:
                seen.add(target)
                result.append(target)
        return result

    def _extract_wiki_links(self, text: str) -> List[str]:
        return self.extract_wiki_links(text)

    def list_notes(self) -> List[Path]:
        """List all markdown files recursively in the vault."""
        return list(self.vault_path.rglob("*.md"))
