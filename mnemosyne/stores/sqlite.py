import json
import logging
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base import MemoryStore

logger = logging.getLogger("mnemosyne-sqlite")


class SQLiteStore(MemoryStore):
    def __init__(self, db_path: str = "mnemosyne.db"):
        self.db_path = db_path
        self._ensure_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist and run incremental column additions."""
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    note_type TEXT NOT NULL DEFAULT 'concept',
                    status TEXT NOT NULL DEFAULT 'active',
                    salience REAL DEFAULT 0.5,
                    embedding TEXT,
                    vault_path TEXT NOT NULL,
                    wing TEXT NOT NULL DEFAULT 'general',
                    room TEXT NOT NULL DEFAULT 'general',
                    origin_agent TEXT NOT NULL DEFAULT 'local',
                    last_accessed_at TEXT NOT NULL DEFAULT (datetime('now')),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(title, vault_path)
                );

                CREATE TABLE IF NOT EXISTS links (
                    id TEXT PRIMARY KEY,
                    source_note_id TEXT NOT NULL,
                    target_note_id TEXT NOT NULL,
                    link_type TEXT NOT NULL DEFAULT 'wiki',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(source_note_id, target_note_id)
                );

                CREATE TABLE IF NOT EXISTS prospective (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT DEFAULT '',
                    trigger_at TEXT NOT NULL,
                    recurring TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    note_title TEXT,
                    query TEXT,
                    summary TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS note_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id TEXT,
                    title TEXT,
                    content TEXT,
                    tags TEXT,
                    salience REAL,
                    version_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """
            )
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(notes);")
            columns = [row["name"] for row in cur.fetchall()]
            if "wing" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN wing TEXT NOT NULL DEFAULT 'general';")
            if "room" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN room TEXT NOT NULL DEFAULT 'general';")
            if "origin_agent" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN origin_agent TEXT NOT NULL DEFAULT 'local';")
            if "last_accessed_at" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN last_accessed_at TEXT NOT NULL DEFAULT '';")

    def _scope_clause(self, scope: Optional[Dict]) -> Tuple[str, List[Any]]:
        if not scope:
            return "", []
        clauses, params = [], []
        if scope.get("wing"):
            clauses.append("wing = ?")
            params.append(scope["wing"])
        if scope.get("room"):
            clauses.append("room = ?")
            params.append(scope["room"])
        return " AND ".join(clauses), params

    def log_timeline(self, action: str, note_title: Optional[str] = None, query: Optional[str] = None, summary: Optional[str] = None) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO timeline (action, note_title, query, summary)
                VALUES (?, ?, ?, ?);
            """,
                (action, note_title, query, summary),
            )

    def get_timeline(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, action, action AS operation, note_title, note_title AS title, query, summary, created_at
                FROM timeline
                ORDER BY id DESC
                LIMIT ?;
            """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_note_history(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT v.id, v.title, v.content AS preview, v.tags, v.salience, v.version_at
                FROM note_versions v
                JOIN notes n ON n.id = v.note_id
                WHERE n.title = ?
                ORDER BY v.id DESC
                LIMIT ?;
            """,
                (title, limit),
            )
            results = []
            for row in cur.fetchall():
                d = dict(row)
                d["tags"] = json.loads(d["tags"]) if d["tags"] else []
                results.append(d)
            return results

    def upsert_note(
        self,
        title: str,
        content: str,
        tags: List[str],
        note_type: str = "concept",
        status: str = "active",
        salience: float = 0.5,
        embedding: Optional[List[float]] = None,
        vault_path: str = "",
        wing: str = "general",
        room: str = "general",
        origin_agent: str = "local",
    ) -> str:
        vault_path = str(vault_path)
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, title, content, tags, salience FROM notes WHERE title = ? AND vault_path = ?;", (title, vault_path))
            existing = cur.fetchone()

            if existing:
                note_id = existing["id"]
                conn.execute(
                    """
                    INSERT INTO note_versions (note_id, title, content, tags, salience)
                    VALUES (?, ?, ?, ?, ?);
                """,
                    (note_id, existing["title"], existing["content"], existing["tags"], existing["salience"]),
                )
                conn.execute(
                    """
                    UPDATE notes
                    SET content = ?, tags = ?, note_type = ?, status = ?, salience = ?,
                        embedding = ?, wing = ?, room = ?, origin_agent = ?, last_accessed_at = datetime('now'), updated_at = datetime('now')
                    WHERE id = ?;
                """,
                    (
                        content,
                        json.dumps(tags),
                        note_type,
                        status,
                        salience,
                        json.dumps(embedding) if embedding else None,
                        wing,
                        room,
                        origin_agent,
                        note_id,
                    ),
                )
            else:
                note_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO notes (id, title, content, tags, note_type, status, salience, embedding, vault_path, wing, room, origin_agent, last_accessed_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'));
                """,
                    (
                        note_id,
                        title,
                        content,
                        json.dumps(tags),
                        note_type,
                        status,
                        salience,
                        json.dumps(embedding) if embedding else None,
                        vault_path,
                        wing,
                        room,
                        origin_agent,
                    ),
                )

            # Real-time incoming link resolution
            cur.execute(
                """
                INSERT OR IGNORE INTO links (id, source_note_id, target_note_id, link_type)
                SELECT lower(hex(randomblob(16))), n.id, ?, 'wiki'
                FROM notes n
                WHERE n.content LIKE ? AND n.status = 'active' AND n.id != ?;
            """,
                (note_id, f"%[[{title}%", note_id),
            )

            return note_id

    def delete_note(self, title: str, vault_path: str = "") -> bool:
        vault_path = str(vault_path)
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM notes WHERE title = ? AND vault_path = ?;", (title, vault_path))
            return cur.rowcount > 0

    def search_semantic(
        self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None, scope: Optional[Dict] = None,
    ) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            where = "WHERE status = 'active' AND embedding IS NOT NULL"
            params = []

            scope_clause, scope_params = self._scope_clause(scope)
            if scope_clause:
                where += " AND " + scope_clause
                params.extend(scope_params)

            if filters:
                if filters.get("note_type"):
                    where += " AND note_type = ?"
                    params.append(filters["note_type"])

            cur.execute(f"SELECT id, title, content, tags, note_type, salience, vault_path, wing, room, embedding FROM notes {where};", params)
            rows = cur.fetchall()

            scored = []
            for row in rows:
                tags = json.loads(row["tags"]) if row["tags"] else []
                if filters and filters.get("tags"):
                    if not any(t in tags for t in filters["tags"]):
                        continue

                try:
                    emb = json.loads(row["embedding"])
                    score = sum(a * b for a, b in zip(query_embedding, emb))
                except Exception:
                    score = 0.0

                scored.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "content": row["content"],
                        "tags": tags,
                        "note_type": row["note_type"],
                        "salience": row["salience"],
                        "vault_path": row["vault_path"],
                        "wing": row["wing"],
                        "room": row["room"],
                        "score": score,
                    }
                )

            scored.sort(key=lambda x: x["score"], reverse=True)
            results = scored[:top_k]

            high_conf = [r["id"] for r in results if r["score"] >= 0.55]
            if high_conf:
                placeholders = ",".join("?" for _ in high_conf)
                conn.execute(f"UPDATE notes SET last_accessed_at = datetime('now') WHERE id IN ({placeholders});", high_conf)

            return results

    def search_keyword(self, query: str, top_k: int = 10, scope: Optional[Dict] = None) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            words = [w for w in re.split(r"\s+", query) if w and len(w) > 1 and w not in ('!', '&', '|', ':')]
            if not words:
                words = [query]

            where_conditions = []
            params = []
            for w in words:
                where_conditions.append("(title LIKE ? OR content LIKE ?)")
                params.extend([f"%{w}%", f"%{w}%"])

            where = "WHERE status = 'active' AND (" + " OR ".join(where_conditions) + ")"

            scope_clause, scope_params = self._scope_clause(scope)
            if scope_clause:
                where += " AND " + scope_clause
                params.extend(scope_params)

            cur.execute(
                f"""
                SELECT id, title, content, tags, note_type, salience, vault_path, wing, room
                FROM notes
                {where}
                ORDER BY salience DESC
                LIMIT ?;
            """,
                params + [top_k],
            )

            results = []
            for row in cur.fetchall():
                results.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "content": row["content"],
                        "tags": json.loads(row["tags"]) if row["tags"] else [],
                        "note_type": row["note_type"],
                        "salience": row["salience"],
                        "vault_path": row["vault_path"],
                        "wing": row["wing"],
                        "room": row["room"],
                        "score": 1.0,
                    }
                )
            if results:
                ids = [r["id"] for r in results]
                placeholders = ",".join("?" for _ in ids)
                conn.execute(f"UPDATE notes SET last_accessed_at = datetime('now') WHERE id IN ({placeholders});", ids)
            return results

    def search_graph(self, note_title: str, depth: int = 2, top_k: int = 10) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM notes WHERE title = ? AND status = 'active';", (note_title,))
            root = cur.fetchone()
            if not root:
                return []

            visited = set()
            current_level = {root["id"]}
            results = []

            for d in range(1, depth + 1):
                if not current_level:
                    break
                next_level = set()
                for nid in current_level:
                    if nid in visited:
                        continue
                    visited.add(nid)
                    cur.execute(
                        """
                        SELECT n.id, n.title, n.content, n.tags, n.salience, n.vault_path, n.wing, n.room
                        FROM links l
                        JOIN notes n ON n.id = l.target_note_id
                        WHERE l.source_note_id = ? AND n.status = 'active';
                    """,
                        (nid,),
                    )
                    for row in cur.fetchall():
                        if row["id"] != root["id"] and row["id"] not in visited:
                            results.append(
                                {
                                    "id": row["id"],
                                    "title": row["title"],
                                    "content": row["content"],
                                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                                    "salience": row["salience"],
                                    "vault_path": row["vault_path"],
                                    "wing": row["wing"],
                                    "room": row["room"],
                                    "depth": d,
                                }
                            )
                            next_level.add(row["id"])
                current_level = next_level

            results.sort(key=lambda x: (x["depth"], -x["salience"]))
            return results[:top_k]

    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        scope: Optional[Dict] = None,
    ) -> List[Dict]:
        semantic = self.search_semantic(query_embedding, top_k=top_k * 2, scope=scope)
        keyword = self.search_keyword(query, top_k=top_k * 2, scope=scope)

        scores: Dict[str, Dict] = {}

        def add_results(results, source, weight):
            for rank, r in enumerate(results, 1):
                nid = str(r["id"])
                if nid not in scores:
                    scores[nid] = dict(r)
                    scores[nid]["rrf_score"] = 0.0
                    scores[nid]["sources"] = []
                scores[nid]["rrf_score"] += weight * (1.0 / (60 + rank))
                scores[nid]["sources"].append(source)

        add_results(semantic, "semantic", 1.0)
        add_results(keyword, "keyword", 0.8)

        for nid in scores:
            scores[nid]["rrf_score"] += scores[nid].get("salience", 0.5) * 0.2

        sorted_results = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        return sorted_results[:top_k]

    def apply_decay(self, decay_rate: float = 0.95, archive_threshold: float = 0.05) -> Dict:
        """Apply Ebbinghaus temporal decay to inactive notes in SQLite."""
        decayed_count = 0
        archived_count = 0
        now = datetime.now(timezone.utc)

        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, salience, tags, last_accessed_at FROM notes WHERE status = 'active';")
            rows = cur.fetchall()

            for row in rows:
                tags = json.loads(row["tags"]) if row["tags"] else []
                # Pinned immunity
                if any(t in tags for t in ["pinned", "permanent", "core"]) or row["salience"] >= 1.0:
                    continue

                last_str = row["last_accessed_at"]
                try:
                    last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    last_dt = now

                days_elapsed = (now - last_dt).total_seconds() / 86400.0
                if days_elapsed >= 1.0:
                    new_salience = row["salience"] * (decay_rate ** days_elapsed)
                    if new_salience < archive_threshold:
                        cur.execute("UPDATE notes SET status = 'archived', salience = ? WHERE id = ?;", (new_salience, row["id"]))
                        archived_count += 1
                    else:
                        cur.execute("UPDATE notes SET salience = ? WHERE id = ?;", (new_salience, row["id"]))
                        decayed_count += 1

            return {"decayed": decayed_count, "archived": archived_count}

    def update_links(self, note_id: str, wiki_links: List[str]) -> None:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM links WHERE source_note_id = ?;", (note_id,))
            for target_title in wiki_links:
                cur.execute("SELECT id FROM notes WHERE title = ? AND status = 'active';", (target_title.strip(),))
                target = cur.fetchone()
                if target:
                    link_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT OR IGNORE INTO links (id, source_note_id, target_note_id, link_type)
                        VALUES (?, ?, ?, 'wiki');
                    """,
                        (link_id, note_id, target["id"]),
                    )

    def reconcile_links(self) -> int:
        """Parse all active notes and rebuild missing links in SQLite."""
        reconciled = 0
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, content FROM notes WHERE status = 'active';")
            notes = cur.fetchall()
            link_pattern = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")

            for note in notes:
                content = note["content"]
                clean = re.sub(r"```[\s\S]*?```", "", content)
                clean = re.sub(r"`[^`]*`", "", clean)
                matches = set(link_pattern.findall(clean))
                for target_title in matches:
                    cur.execute("SELECT id FROM notes WHERE title = ? AND status = 'active';", (target_title.strip(),))
                    target = cur.fetchone()
                    if target and target["id"] != note["id"]:
                        cur.execute(
                            """
                            INSERT OR IGNORE INTO links (id, source_note_id, target_note_id, link_type)
                            VALUES (?, ?, ?, 'wiki');
                        """,
                            (str(uuid.uuid4()), note["id"], target["id"]),
                        )
                        if cur.rowcount > 0:
                            reconciled += 1
        return reconciled

    def get_stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM notes WHERE status = 'active';")
            notes = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM notes WHERE status = 'archived';")
            archived = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM links;")
            links = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM prospective WHERE status = 'pending';")
            pending_reminders = cur.fetchone()[0]
            cur.execute("SELECT DISTINCT wing FROM notes WHERE status = 'active';")
            wings = [row[0] for row in cur.fetchall()]
            return {
                "notes": notes,
                "archived": archived,
                "links": links,
                "pending_reminders": pending_reminders,
                "wings": wings,
                "backend": "sqlite",
            }
