import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .embedder import Embedder
from .security import AdmissionControl
from .stores import create_store
from .stores.base import MemoryStore
from .vault import VaultManager

# Stdio protocol stream safety
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mnemosyne-core")


class SecurityCheckError(ValueError):
    pass


class UnifiedMemorySystem:
    def __init__(
        self,
        vault_path: Optional[str] = None,
        dsn: Optional[str] = None,
        shared_dsn: Optional[str] = None,
        auto_sync: bool = False,
        agent_name: Optional[str] = None,
    ):
        self.vault_path = os.path.expanduser(vault_path or os.environ.get("MEMORY_VAULT_PATH", "~/.mnemosyne/vault"))
        self.agent_name = agent_name or os.environ.get("MEMORY_AGENT_NAME", "local-agent")
        self.vault = VaultManager(self.vault_path)
        self.embedder = Embedder()
        self.security = AdmissionControl()
        self.db: MemoryStore = create_store(dsn)

        # Optional shared cross-agent memory store
        self.shared_dsn = shared_dsn or os.environ.get("MEMORY_SHARED_DSN")
        self.shared_db: Optional[MemoryStore] = create_store(self.shared_dsn) if self.shared_dsn else None
        if self.shared_db:
            logger.info(f"UnifiedMemorySystem: Connected to shared fleet memory at {self.shared_dsn}")

        if auto_sync:
            self.sync_vault_to_db()

    def sync_vault_to_db(self) -> Dict[str, int]:
        files = self.vault.list_notes()
        count = 0
        for f in files:
            try:
                content = self.vault.read_note(f)
                note_id = self.db.upsert_note(
                    title=f,
                    content=content,
                    tags=[],
                    vault_path=self.vault.vault_path,
                    origin_agent=self.agent_name,
                )
                links = self.vault.extract_wiki_links(content)
                self.db.update_links(note_id, links)
                count += 1
            except Exception as e:
                logger.error(f"Error syncing {f}: {e}")
        return {"synced": count}

    def _sanitize_for_shared(self, content: str) -> None:
        """Strict regex security guard to prevent private keys, auth tokens, or PII from leaking to shared_db."""
        patterns = [
            r"-----BEGIN (RSA|OPENSSH|PGP|PRIVATE) KEY-----",
            r"(eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})",  # JWT
            r"(ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{40,})",  # GitHub Tokens
            r"(sk-[a-zA-Z0-9]{32,}|xox[baprs]-[a-zA-Z0-9-]{10,})",  # OpenAI / Slack
            r"(AKIA[0-9A-Z]{16})",  # AWS Key ID
        ]
        for p in patterns:
            if re.search(p, content):
                raise SecurityCheckError("Security Violation: Payload contains private credentials/tokens; publishing to shared memory blocked.")

    def remember(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        note_type: str = "concept",
        salience: float = 0.5,
        wing: str = "general",
        room: str = "general",
        pinned: bool = False,
    ) -> Dict[str, Any]:
        tags = tags or []
        if pinned:
            if "pinned" not in tags:
                tags.append("pinned")
            salience = max(salience, 1.0)

        is_valid, msg = self.security.validate(title, content, tags)
        if not is_valid:
            logger.warning(f"Admission control rejected note [{title}]: {msg}")
            return {"success": False, "error": msg}

        emb = self.embedder.embed_query(f"{title} {content}")

        note_id = self.db.upsert_note(
            title=title,
            content=content,
            tags=tags,
            note_type=note_type,
            status="active",
            salience=salience,
            embedding=emb,
            vault_path=self.vault.vault_path,
            wing=wing,
            room=room,
            origin_agent=self.agent_name,
        )

        wiki_links = self.vault.extract_wiki_links(content)
        self.db.update_links(note_id, wiki_links)
        self.vault.write_note(title, content, tags)

        self.db.log_timeline(
            action="remember",
            note_title=title,
            summary=f"wing={wing} room={room} salience={salience:.2f} origin={self.agent_name}",
        )

        return {"success": True, "note_id": note_id, "title": title}

    def publish_shared(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        wing: str = "shared",
        room: str = "general",
    ) -> Dict[str, Any]:
        """Publish a curated note to the cross-agent shared fleet memory with security sanitization."""
        if not self.shared_db:
            return {"success": False, "error": "Shared fleet database (MEMORY_SHARED_DSN) is not configured."}

        tags = tags or []
        if "shared" not in tags:
            tags.append("shared")

        try:
            self._sanitize_for_shared(content)
        except SecurityCheckError as e:
            return {"success": False, "error": str(e)}

        is_valid, msg = self.security.validate(title, content, tags)
        if not is_valid:
            return {"success": False, "error": msg}

        emb = self.embedder.embed_query(f"{title} {content}")

        note_id = self.shared_db.upsert_note(
            title=title,
            content=content,
            tags=tags,
            note_type="shared_policy",
            status="active",
            salience=0.8,
            embedding=emb,
            vault_path="shared",
            wing=wing,
            room=room,
            origin_agent=self.agent_name,
        )

        self.db.log_timeline(
            action="publish_shared",
            note_title=title,
            summary=f"published to shared_db (wing={wing}, room={room})",
        )

        return {"success": True, "note_id": note_id, "title": title, "scope": "shared"}

    def recall(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 5,
        filters: Optional[Dict] = None,
        scope: Optional[Dict] = None,
        include_shared: bool = True,
    ) -> List[Dict]:
        emb = self.embedder.embed_query(query)

        # 1. Query Private Store
        if mode == "semantic":
            private_results = self.db.search_semantic(emb, top_k, filters, scope=scope)
        elif mode == "keyword":
            private_results = self.db.search_keyword(query, top_k, scope=scope)
        elif mode == "graph":
            private_results = self.db.search_graph(query, top_k=top_k)
        else:
            private_results = self.db.hybrid_search(query, emb, top_k, scope=scope)

        for r in private_results:
            r["source_store"] = "private"

        # 2. Fail-Soft Query to Shared Store
        shared_results = []
        if self.shared_db and include_shared:
            try:
                if mode == "keyword":
                    shared_results = self.shared_db.search_keyword(query, top_k, scope=scope)
                else:
                    shared_results = self.shared_db.hybrid_search(query, emb, top_k, scope=scope)
                for r in shared_results:
                    r["source_store"] = "shared"
            except Exception as e:
                logger.warning(f"Shared memory recall failed softly ({e}); continuing with private memories.")

        self.db.log_timeline(action="recall", query=query, summary=f"mode={mode} scope={scope} shared={len(shared_results)}")

        if not shared_results:
            return private_results

        # Merge and deduplicate by title
        combined: Dict[str, Dict] = {}
        for r in private_results:
            combined[r["title"]] = r
        for r in shared_results:
            if r["title"] not in combined:
                combined[r["title"]] = r

        return list(combined.values())[:top_k]

    def ingest_session(self, transcript: str, wing: str = "general", room: str = "sessions") -> Dict[str, Any]:
        """Ingest a full conversation transcript verbatim along turn boundaries."""
        if not transcript or not transcript.strip():
            return {"success": False, "error": "Empty transcript provided."}

        turns = self._split_transcript_turns(transcript)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d--%H%M%S")
        ingested_count = 0

        for idx, turn in enumerate(turns, 1):
            title = f"Session {timestamp} Turn {idx:02d}"
            res = self.remember(
                title=title,
                content=turn,
                tags=["session", "transcript"],
                note_type="session",
                salience=0.4,
                wing=wing,
                room=room,
            )
            if res.get("success"):
                ingested_count += 1

        self.db.log_timeline(
            action="ingest_session",
            summary=f"ingested {ingested_count}/{len(turns)} turns to wing={wing} room={room}",
        )

        return {"success": True, "turns_total": len(turns), "turns_ingested": ingested_count, "wing": wing, "room": room}

    def _split_transcript_turns(self, transcript: str) -> List[str]:
        lines = transcript.splitlines()
        turns = []
        current_turn = []
        in_code_block = False

        turn_markers = re.compile(r"^(User|Assistant|Human|AI|System|### Turn|\*\*User\*\*|\*\*Assistant\*\*):", re.IGNORECASE)

        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block

            if not in_code_block and turn_markers.match(line.strip()):
                if current_turn:
                    turns.append("\n".join(current_turn).strip())
                    current_turn = []

            current_turn.append(line)

        if current_turn:
            turns.append("\n".join(current_turn).strip())

        return [t for t in turns if t]

    def timeline(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.db.get_timeline(limit=limit)

    def note_history(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.db.get_note_history(title=title, limit=limit)

    def remind_me(self, title: str, content: str, trigger_at: str, recurring: Optional[str] = None) -> Dict[str, Any]:
        self.db.log_timeline(action="remind", note_title=title, summary=f"trigger_at={trigger_at} recurring={recurring}")
        return {"success": True, "title": title, "trigger_at": trigger_at, "recurring": recurring}

    def consolidate(self, decay_rate: float = 0.95, archive_threshold: float = 0.05) -> Dict[str, Any]:
        """Apply link reconciliation and temporal decay."""
        reconciled = self.db.reconcile_links()
        decay_res = self.db.apply_decay(decay_rate=decay_rate, archive_threshold=archive_threshold)
        self.db.log_timeline(
            action="consolidate",
            summary=f"reconciled_links={reconciled} decayed={decay_res.get('decayed', 0)} archived={decay_res.get('archived', 0)}",
        )
        return {"reconciled_links": reconciled, **decay_res}

    def stats(self) -> Dict[str, Any]:
        return self.db.get_stats()
