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
from .consolidation import ConsolidationEngine
from .prospective import ProspectiveMemory

# Stdio stream protection
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mnemosyne-core")


class SecurityCheckError(ValueError):
    pass


def _neutralize_control_tokens(text: str) -> str:
    """
    Neutralize LLM prompt injection control tokens in prose while preserving
    exact text inside markdown code blocks (``` ... ```) and inline code (`...`).
    """
    if not text:
        return ""

    tokens_to_neutralize = [
        (r"<\|im_start\|>", "<\u200b|im_start|\u200b>"),
        (r"<\|system\|>", "<\u200b|system|\u200b>"),
        (r"<\|user\|>", "<\u200b|user|\u200b>"),
        (r"<\|assistant\|>", "<\u200b|assistant|\u200b>"),
        (r"\[INST\]", "[\u200bINST\u200b]"),
        (r"\[/INST\]", "[\u200b/INST\u200b]"),
        (r"<<SYS>>", "<\u200b<SYS>\u200b>"),
        (r"<</SYS>>", "<\u200b</SYS>\u200b>"),
    ]

    parts = re.split(r"(```[\s\S]*?```|`[^`]*?`)", text)
    processed = []
    for part in parts:
        if part.startswith("`"):
            # Inside code block -> preserve verbatim
            processed.append(part)
        else:
            # Prose text -> neutralize control markers
            cur = part
            for pat, repl in tokens_to_neutralize:
                cur = re.sub(pat, repl, cur, flags=re.IGNORECASE)
            processed.append(cur)
    return "".join(processed)


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

        # Reconcile orphaned maintenance modules back into the core system
        self.consolidation_engine = ConsolidationEngine(self.db, self.vault, self.embedder)
        self.prospective = ProspectiveMemory(self.db)

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
                content = self.vault.read_note(f.stem)
                if content:
                    raw = content.get("content", "")
                    note_id = self.db.upsert_note(
                        title=f.stem,
                        content=raw,
                        tags=content.get("frontmatter", {}).get("tags", []),
                        vault_path=str(self.vault.vault_path),
                        origin_agent=self.agent_name,
                    )
                    links = self.vault.extract_wiki_links(raw)
                    self.db.update_links(note_id, links)
                    count += 1
            except Exception as e:
                logger.error(f"Error syncing {f}: {e}")
        return {"synced": count}

    def _sanitize_for_shared(self, content: str) -> None:
        """Strict regex security guard to prevent private keys, auth tokens, or credentials from leaking to shared_db."""
        patterns = [
            r"-----BEGIN (RSA|OPENSSH|PGP|PRIVATE|EC|DSA) KEY-----",
            r"(eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})",  # JWT
            r"(ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{40,})",  # GitHub Tokens
            r"(sk-ant-api\d\d-[a-zA-Z0-9_\-]{50,}|sk-ant-[a-zA-Z0-9_\-]{20,})",  # Anthropic Claude API Keys
            r"(AIza[0-9A-Za-z_\-]{30,35})",  # Google Gemini / Cloud API Keys
            r"(hf_[a-zA-Z0-9]{34})",  # HuggingFace Hub Tokens
            r"(sk-[a-zA-Z0-9]{32,}|sk-proj-[a-zA-Z0-9_\-]{40,})",  # OpenAI API Keys
            r"(xox[baprs]-[a-zA-Z0-9\-]{10,})",  # Slack Tokens
            r"(AKIA[0-9A-Z]{16})",  # AWS Access Key ID
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

        # Code-block-aware injection neutralization
        safe_content = _neutralize_control_tokens(content)

        is_valid, msg = self.security.validate(title, safe_content, tags)
        if not is_valid:
            logger.warning(f"Admission control rejected note [{title}]: {msg}")
            return {"success": False, "error": msg}

        emb = self.embedder.embed_query(f"{title} {safe_content}")
        wiki_links = self.vault.extract_wiki_links(safe_content)

        # 1. Write to physical Markdown vault first (atomic write)
        try:
            written_path = self.vault.write_note(
                title=title,
                content=safe_content,
                tags=tags,
                note_type=note_type,
                status="active",
                salience=salience,
                links=wiki_links,
                wing=wing,
                room=room,
            )
        except Exception as e:
            logger.error(f"Failed writing note [{title}] to vault: {e}")
            return {"success": False, "error": f"Vault write failed: {e}"}

        # 2. Commit to database with rollback protection
        try:
            note_id = self.db.upsert_note(
                title=title,
                content=safe_content,
                tags=tags,
                note_type=note_type,
                status="active",
                salience=salience,
                embedding=emb,
                vault_path=str(self.vault.vault_path),
                wing=wing,
                room=room,
                origin_agent=self.agent_name,
            )
            self.db.update_links(note_id, wiki_links)
            self.db.log_timeline(
                action="remember",
                note_title=title,
                summary=f"wing={wing} room={room} salience={salience:.2f} origin={self.agent_name}",
            )
            return {"success": True, "note_id": note_id, "title": title}
        except Exception as e:
            logger.error(f"Database upsert failed for note [{title}]: {e}; rolling back vault file.")
            try:
                if written_path.exists():
                    written_path.unlink()
            except Exception as cleanup_err:
                logger.warning(f"Failed to remove vault file on rollback: {cleanup_err}")
            return {"success": False, "error": f"Database write failed: {e}"}

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

        safe_content = _neutralize_control_tokens(content)
        is_valid, msg = self.security.validate(title, safe_content, tags)
        if not is_valid:
            return {"success": False, "error": msg}

        emb = self.embedder.embed_query(f"{title} {safe_content}")

        try:
            note_id = self.shared_db.upsert_note(
                title=title,
                content=safe_content,
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
        except Exception as e:
            logger.error(f"Failed publishing note [{title}] to shared database: {e}")
            return {"success": False, "error": f"Shared database write failed: {e}"}

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

        merged_dict: Dict[str, Dict] = {}
        for r in private_results:
            merged_dict[r["title"]] = r
        for r in shared_results:
            if r["title"] not in merged_dict:
                merged_dict[r["title"]] = r

        # Sort merged results by relevance (rrf_score or score) so high-value shared memories rank properly
        sorted_results = sorted(
            merged_dict.values(),
            key=lambda x: x.get("rrf_score", x.get("score", 0.0)),
            reverse=True
        )
        results = sorted_results[:top_k]

        # Enclose memory content in structured XML context tags with tag escaping
        for r in results:
            content_raw = r.get("content", "")
            safe_text = (
                content_raw.replace("</recalled_memory_context>", "<\\/recalled_memory_context>")
                .replace("<recalled_memory_context", "<\\recalled_memory_context")
            )
            r["formatted_context"] = (
                f'<recalled_memory_context id="{r.get("id")}" title="{r.get("title")}" '
                f'wing="{r.get("wing", "general")}" room="{r.get("room", "general")}" '
                f'source="{r.get("source_store", "private")}">\n'
                f"{safe_text}\n"
                f"</recalled_memory_context>"
            )

        return results

    def assemble_context(
        self,
        query: str,
        max_tokens: int = 2000,
        top_k: int = 10,
        scope: Optional[Dict] = None,
        mode: str = "hybrid",
        include_shared: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieve, deduplicate, rank, and assemble top memories into a token-budgeted XML prompt block.
        Token estimation: standard heuristic of ~4 characters per token.
        """
        candidates = self.recall(
            query=query,
            mode=mode,
            top_k=top_k,
            scope=scope,
            include_shared=include_shared,
        )

        char_budget = max_tokens * 4
        current_chars = 0
        packed_notes = []
        context_blocks = []

        for note in candidates:
            title = note.get("title", "")
            content = note.get("content", "")
            tags = note.get("tags", [])
            wing = note.get("wing", "general")
            room = note.get("room", "general")
            salience = note.get("salience", 0.5)
            source = note.get("source_store", "private")

            tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
            safe_content = (
                content.replace("</recalled_memory>", "<\\/recalled_memory>")
                .replace("<recalled_memory", "<\\recalled_memory")
            )

            block = (
                f'<recalled_memory title="{title}" wing="{wing}" room="{room}" salience="{salience:.2f}" source="{source}" tags="{tags_str}">\n'
                f"{safe_content}\n"
                f"</recalled_memory>"
            )

            block_chars = len(block) + 2
            if current_chars + block_chars > char_budget and packed_notes:
                break

            packed_notes.append(note)
            context_blocks.append(block)
            current_chars += block_chars

        if context_blocks:
            context_text = "<memory_context>\n" + "\n".join(context_blocks) + "\n</memory_context>"
        else:
            context_text = "<memory_context>\n<!-- No matching memories found within budget -->\n</memory_context>"

        estimated_tokens = max(1, len(context_text) // 4)

        return {
            "context_text": context_text,
            "estimated_tokens": estimated_tokens,
            "max_tokens": max_tokens,
            "notes_included": len(packed_notes),
            "notes": [
                {
                    "title": n.get("title"),
                    "wing": n.get("wing"),
                    "room": n.get("room"),
                    "salience": n.get("salience"),
                    "source": n.get("source_store"),
                }
                for n in packed_notes
            ],
        }

    def ingest_session(self, transcript: str, wing: str = "general", room: str = "sessions") -> Dict[str, Any]:
        """
        Ingest a full conversation transcript verbatim along turn boundaries,
        applying linear sequence sliding-window chunking for turns > 1,500 chars.
        """
        if not transcript or not transcript.strip():
            return {"success": False, "error": "Empty transcript provided."}

        turns = self._split_transcript_turns(transcript)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d--%H%M%S")
        ingested_count = 0

        for idx, turn in enumerate(turns, 1):
            if len(turn) > 1500:
                chunks = self._chunk_text(turn, max_chars=1500, overlap=200)
                for c_idx, chunk in enumerate(chunks, 1):
                    title = f"Session {timestamp} Turn {idx:02d} Part {c_idx:02d}"
                    next_link = f"\n\n[[Session {timestamp} Turn {idx:02d} Part {c_idx+1:02d}]]" if c_idx < len(chunks) else ""
                    res = self.remember(
                        title=title,
                        content=chunk + next_link,
                        tags=["session", "transcript", "chunk"],
                        note_type="session",
                        salience=0.3,
                        wing=wing,
                        room=room,
                    )
                    if res.get("success"):
                        ingested_count += 1
            else:
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
            summary=f"ingested {ingested_count} units from {len(turns)} turns into wing={wing} room={room}",
        )

        return {"success": True, "turns_total": len(turns), "units_ingested": ingested_count, "wing": wing, "room": room}

    def _chunk_text(self, text: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            chunks.append(text[start:end])
            start += max_chars - overlap
        return chunks

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
        """Schedule a future reminder through the prospective-memory engine.

        Returns success:False if the backend cannot actually schedule, so callers
        (e.g. the MCP `memory_remind_me` tool) never report a reminder that was
        silently dropped.
        """
        if getattr(self, "prospective", None) is None:
            self.db.log_timeline(action="remind", note_title=title, summary=f"trigger_at={trigger_at} recurring={recurring}")
            return {"success": False, "error": "prospective memory engine is not initialized", "title": title}

        try:
            reminder_id = self.prospective.schedule(title, content, trigger_at, recurring)
        except Exception as e:
            logger.warning(f"Prospective schedule failed ({e}); reminder NOT scheduled.")
            self.db.log_timeline(action="remind", note_title=title, summary=f"FAILED trigger_at={trigger_at} recurring={recurring} err={e}")
            return {
                "success": False,
                "error": f"Failed to schedule reminder: {e}",
                "title": title,
                "trigger_at": trigger_at,
                "recurring": recurring,
                "reminder_id": None,
            }

        self.db.log_timeline(action="remind", note_title=title, summary=f"trigger_at={trigger_at} recurring={recurring}")
        return {
            "success": True,
            "title": title,
            "trigger_at": trigger_at,
            "recurring": recurring,
            "reminder_id": reminder_id,
        }

    def check_reminders(self, window_hours: int = 24) -> List[Dict[str, Any]]:
        """Return reminders due within the next N hours (if backend supports it)."""
        if getattr(self, "prospective", None) is None:
            return []
        try:
            return self.prospective.get_due(window_hours=window_hours)
        except Exception as e:
            logger.warning(f"check_reminders failed: {e}")
            return []

    def consolidate(self, decay_rate: float = 0.95, archive_threshold: float = 0.05) -> Dict[str, Any]:
        """Run temporal decay and link reconciliation, then engine-level consolidation.

        Prefers the ConsolidationEngine when available; always applies the
        store-level decay/reconcile so the behavior remains deterministic.
        """
        reconciled = self.db.reconcile_links()
        decay_res = self.db.apply_decay(decay_rate=decay_rate, archive_threshold=archive_threshold)
        self.db.log_timeline(
            action="consolidate",
            summary=f"reconciled_links={reconciled} decayed={decay_res.get('decayed', 0)} archived={decay_res.get('archived', 0)}",
        )
        engine_res: Dict[str, Any] = {}
        if getattr(self, "consolidation_engine", None) is not None:
            try:
                engine_res = self.consolidation_engine.run(
                    decay_factor=decay_rate, archive_threshold=archive_threshold
                )
            except Exception as e:
                logger.warning(f"ConsolidationEngine run failed ({e}); store-level consolidation still applied.")
        return {"reconciled_links": reconciled, **decay_res, "engine": engine_res}

    def stats(self) -> Dict[str, Any]:
        return self.db.get_stats()
