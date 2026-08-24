"""
Mnemosyne Core — Unified Memory System (v3.0).
Combines Markdown Vault, PostgreSQL/SQLite, Embedder, Security, and Prospective Memory.
"""

import os
import re
import logging
from typing import List, Dict, Optional, Any

from mnemosyne.vault import VaultManager
from mnemosyne.stores import create_store, MemoryStore
from mnemosyne.embedder import Embedder, EMBEDDING_DIM
from mnemosyne.security import AdmissionControl, SalienceEngine
from mnemosyne.prospective import ProspectiveMemory
from mnemosyne.consolidation import ConsolidationEngine

logger = logging.getLogger("unified-memory")


class UnifiedMemorySystem:
    """Unified Memory System orchestrating storage, vector retrieval, and prospective triggers."""

    def __init__(
        self,
        vault_path: Optional[str] = None,
        dsn: Optional[str] = None,
        embedder: Optional[Embedder] = None,
        auto_sync: bool = False,
    ) -> None:
        self.vault = VaultManager(vault_path) if vault_path else VaultManager()
        self.embedder = embedder or Embedder()
        self.db: MemoryStore = create_store(dsn)
        self.admission = AdmissionControl(self.db, self.embedder)
        self.salience = SalienceEngine()
        self.prospective = ProspectiveMemory(self.db)
        self.consolidation = ConsolidationEngine(self.db, self.vault, self.embedder)

        if auto_sync:
            try:
                self.sync()
            except Exception as e:
                logging.warning(f"Auto-sync failed: {e}. Call memory.sync() manually.")

    def remember(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        note_type: str = "concept",
        links: Optional[List[str]] = None,
        salience: Optional[float] = None,
        wing: str = "general",
        room: str = "general",
        pinned: bool = False,
    ) -> Dict:
        """
        Write a memory with hierarchical scoping and optional pinned immunity.
        Returns: {"success": bool, "note_id": str, "reason": str}
        """
        tags = list(tags) if tags else []
        links = links or []

        if pinned and "pinned" not in tags:
            tags.append("pinned")

        is_valid, reason = self.admission.validate(title, content, tags)
        if not is_valid:
            logger.warning(f"Admission rejected: {title} — {reason}")
            return {"success": False, "note_id": None, "reason": reason}

        if salience is None:
            salience = 1.0 if pinned else self.salience.score(
                {"type": note_type, "tags": tags}, content, self.db.get_stats()
            )

        self.vault.write_note(title, content, tags, note_type, "active", salience, links)
        embedding = self.embedder.embed([content])[0] if content else [0.0] * EMBEDDING_DIM
        note_id = self.db.upsert_note(
            title,
            content,
            tags,
            note_type,
            "active",
            salience,
            embedding,
            str(self.vault.vault_path),
            wing=wing,
            room=room,
        )
        self.db.update_links(note_id, links)
        self.db.log_timeline("remember", note_title=title, summary=f"wing={wing} room={room} salience={salience:.2f}")
        logger.info(f"Remembered: {title} [{wing}/{room}] (salience={salience:.2f})")
        return {"success": True, "note_id": note_id, "reason": reason}

    def recall(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 10,
        filters: Optional[Dict] = None,
        scope: Optional[Dict] = None,
    ) -> List[Dict]:
        """Search memories with optional wing/room scoping. mode: hybrid, semantic, keyword, graph."""
        self.db.log_timeline("recall", query=query, summary=f"mode={mode} scope={scope}")

        if mode == "semantic":
            emb = self.embedder.embed([query])[0]
            return self.db.search_semantic(emb, top_k, filters, scope=scope)
        elif mode == "keyword":
            return self.db.search_keyword(query, top_k, scope=scope)
        elif mode == "graph":
            return self.db.search_graph(query, depth=2, top_k=top_k)
        else:
            emb = self.embedder.embed([query])[0]
            return self.db.hybrid_search(query, emb, top_k, scope=scope)

    def ingest_session(self, transcript: str, wing: str = "general", room: str = "sessions") -> Dict:
        """
        Ingest a full conversation transcript verbatim.
        Splits on conversation turn boundaries (User/Assistant/Headers) rather than naive character slicing.
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        # Split along turns (User:, Human:, Assistant:, AI:, or ### headers)
        turn_pattern = r"(?:\n\n(?=(?:User|Human|Assistant|AI|System|Agent|###\s+|---\s*\n)))"
        raw_turns = re.split(turn_pattern, transcript.strip(), flags=re.IGNORECASE)

        chunks = []
        current_chunk = ""

        for turn in raw_turns:
            turn = turn.strip()
            if not turn:
                continue

            if len(current_chunk) + len(turn) > 1500 and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = turn
            else:
                current_chunk = f"{current_chunk}\n\n{turn}".strip() if current_chunk else turn

        if current_chunk:
            chunks.append(current_chunk.strip())

        if not chunks:
            chunks = [transcript.strip()] if transcript.strip() else []

        saved = 0
        for i, chunk in enumerate(chunks):
            title = f"session-{timestamp}-{i:03d}"
            result = self.remember(
                title=title,
                content=chunk,
                tags=["session", "verbatim"],
                note_type="session",
                wing=wing,
                room=room,
                salience=0.4,
            )
            if result.get("success"):
                saved += 1

        self.db.log_timeline("ingest_session", summary=f"chunks={len(chunks)} saved={saved} wing={wing}")
        return {"chunks": len(chunks), "saved": saved, "wing": wing, "room": room}

    def timeline(self, limit: int = 20) -> List[Dict]:
        """Get recent memory operations."""
        return self.db.get_timeline(limit)

    def history(self, title: str, limit: int = 10) -> List[Dict]:
        """Get version history for a specific note."""
        return self.db.get_note_history(title, limit)

    def remind_me(
        self,
        title: str,
        trigger_at: str,
        content: str = "",
        recurring: Optional[str] = None,
    ) -> str:
        """Schedule a prospective reminder."""
        reminder_id = self.prospective.schedule(title, trigger_at, content, recurring)
        self.db.log_timeline("remind", note_title=title, summary=f"trigger_at={trigger_at} recurring={recurring}")
        return reminder_id

    def check_reminders(self, window_hours: int = 24) -> List[Dict]:
        """Check due reminders."""
        return self.prospective.check_due(window_hours)

    def consolidate(self, decay_rate: float = 0.95, archive_threshold: float = 0.05) -> Dict:
        """Run sleep consolidation: apply temporal decay and archive stale notes."""
        res = self.db.apply_decay(decay_rate, archive_threshold)
        self.db.log_timeline(
            "consolidate",
            summary=f"decayed={res.get('decayed', 0)} archived={res.get('archived', 0)}",
        )
        return res

    def sync(self) -> Dict:
        """Sync markdown files from the vault into the database."""
        return self.vault.sync_to_db(self.db, self.embedder)

    def stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return self.db.get_stats()
