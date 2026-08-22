"""Vault manager for Obsidian-compatible markdown files."""

import os
import re
import unicodedata
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("unified-memory")

VAULT_PATH = os.environ.get(
    "MEMORY_VAULT_PATH", "/Users/mohamedfathy/Documents/Kimi/Workspaces/Mnemosyne/obsidian-vault"
)


def safe_filename(title: str) -> str:
    """Convert a title to a safe filename."""
    normalized = unicodedata.normalize("NFKC", title)
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", normalized)
    safe = safe.strip()[:200]
    return safe + ".md" if safe else "untitled.md"


class VaultManager:
    """
    Manages the Obsidian-compatible markdown vault.
    Files are the source of truth; the database is a rebuildable index.
    """

    def __init__(self, vault_path: str = VAULT_PATH) -> None:
        self.vault_path = Path(vault_path)
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
    ) -> Path:
        """Write a note to the vault."""
        tags = tags or []
        links = links or []
        filepath = self.vault_path / safe_filename(title)

        frontmatter = {
            "title": title,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "tags": tags,
            "type": note_type,
            "status": status,
            "salience": salience,
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
        filepath.write_text(full, encoding="utf-8")
        return filepath

    def read_note(self, title: str) -> Optional[Dict]:
        """Read a note from the vault. Returns dict with frontmatter + content."""
        filepath = self.vault_path / safe_filename(title)
        if not filepath.exists():
            return None
        text = filepath.read_text(encoding="utf-8")
        result = self._parse_note(text)
        result["title"] = result["frontmatter"].get("title", title)
        # Extract clean content (strip title heading if present)
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
        """Extract [[Wiki Links]] from text."""
        return re.findall(r"\[\[(.*?)\]\]", text)

    def _extract_wiki_links(self, text: str) -> List[str]:
        """Private alias for extract_wiki_links."""
        return self.extract_wiki_links(text)

    def list_notes(self) -> List[Path]:
        """List all markdown files in the vault."""
        return list(self.vault_path.glob("*.md"))

    def sync_to_db(self, db, embedder) -> Dict:
        """Sync all vault files to the database."""
        from mnemosyne.embedder import EMBEDDING_DIM

        stats = {"upserted": 0, "deleted": 0, "errors": 0}
        for filepath in self.list_notes():
            try:
                text = filepath.read_text(encoding="utf-8")
                parsed = self._parse_note(text)
                fm = parsed["frontmatter"]
                title = fm.get("title", filepath.stem.replace("-", " "))
                content = parsed["body"]
                tags = fm.get("tags", [])
                note_type = fm.get("type", "concept")
                status = fm.get("status", "active")
                salience = float(fm.get("salience", 0.5))
                embedding = embedder.embed([content])[0] if content else [0.0] * EMBEDDING_DIM
                note_id = db.upsert_note(
                    title,
                    content,
                    tags,
                    note_type,
                    status,
                    salience,
                    embedding,
                    str(self.vault_path),
                )
                wiki_links = self.extract_wiki_links(text)
                db.update_links(note_id, wiki_links)
                stats["upserted"] += 1
            except Exception as e:
                logger.error(f"Sync error for {filepath}: {e}")
                stats["errors"] += 1
        logger.info(f"Vault sync complete: {stats}")
        return stats
