"""Unified Memory System v3.0 — main API class."""

import logging
from typing import List, Dict, Optional

from mnemosyne.vault import VaultManager, VAULT_PATH
from mnemosyne.stores import create_store
from mnemosyne.stores.postgres import DB_DSN
from mnemosyne.embedder import Embedder, EMBEDDING_DIM
from mnemosyne.security import AdmissionControl, SalienceEngine
from mnemosyne.prospective import ProspectiveMemory
from mnemosyne.consolidation import ConsolidationEngine

logger = logging.getLogger("unified-memory")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class UnifiedMemorySystem:
    """
    Mnemosyne v3.0 — Unified Memory with hierarchical scoping,
    temporal decay, timeline logging, and versioning.
    """

    def __init__(self, vault_path: str = VAULT_PATH, dsn: str = DB_DSN, auto_sync: bool = False) -> None:
        self.vault = VaultManager(vault_path)
        self.db = create_store(dsn)
        self.embedder = Embedder()
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
    ) -> Dict:
        """
        Write a memory with hierarchical scoping.
        Returns: {"success": bool, "note_id": str, "reason": str}
        """
        tags = tags or []
        links = links or []
        is_valid, reason = self.admission.validate(title, content, tags)
        if not is_valid:
            logger.warning(f"Admission rejected: {title} — {reason}")
            return {"success": False, "note_id": None, "reason": reason}

        if salience is None:
            salience = self.salience.score(
                {"type": note_type, "tags": tags}, content, self.db.get_stats()
            )

        self.vault.write_note(title, content, tags, note_type, "active", salience, links)
        embedding = self.embedder.embed([content])[0] if content else [0.0] * EMBEDDING_DIM
        note_id = self.db.upsert_note(
            title, content, tags, note_type, "active", salience, embedding,
            str(self.vault.vault_path), wing=wing, room=room,
        )
        self.db.update_links(note_id, links)
        self.db.log_timeline("remember", note_title=title, summary=f"wing={wing} room={room} salience={salience:.2f}")
        logger.info(f"Remembered: {title} [{wing}/{room}] (salience={salience:.2f})")
        return {"success": True, "note_id": note_id, "reason": reason}

    def recall(
        self, query: str, mode: str = "hybrid", top_k: int = 10,
        filters: Optional[Dict] = None, scope: Optional[Dict] = None,
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
        Chunks it into ~1000 char segments and stores each as a separate memory.
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        chunks = []
        current = ""
        for line in transcript.split("\n"):
            current += line + "\n"
            if len(current) > 1000:
                chunks.append(current.strip())
                current = ""
        if current.strip():
            chunks.append(current.strip())

        saved = 0
        for i, chunk in enumerate(chunks):
            title = f"session-{timestamp}-{i:03d}"
            result = self.remember(
                title=title, content=chunk, tags=["session", "verbatim"],
                note_type="session", wing=wing, room=room, salience=0.4,
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
        self, title: str, trigger_at: str, content: str = "", recurring: Optional[str] = None
    ) -> str:
        rid = self.prospective.schedule(title, content, trigger_at, recurring)
        self.db.log_timeline("remind", note_title=title, summary=f"trigger={trigger_at} recurring={recurring}")
        return rid

    def check_reminders(self) -> List[Dict]:
        return self.prospective.get_due(window_hours=24)

    def consolidate(self) -> Dict:
        """Run sleep-time consolidation with temporal decay."""
        consolidation_result = self.consolidation.run()
        try:
            decay_result = self.db.apply_decay(decay_rate=0.95, archive_threshold=0.05)
            consolidation_result["decay"] = decay_result
            self.db.log_timeline("consolidate", summary=f"decay={decay_result}")
        except Exception as e:
            logger.warning(f"Decay failed: {e}")
            consolidation_result["decay"] = {"error": str(e)}
        return consolidation_result

    def sync(self) -> Dict:
        return self.vault.sync_to_db(self.db, self.embedder)

    def stats(self) -> Dict:
        return self.db.get_stats()
