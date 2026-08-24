"""SQLite store with pure-Python vector similarity and full v3.0 feature parity."""

import os
import json
import math
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from mnemosyne.stores.base import MemoryStore

logger = logging.getLogger("unified-memory")

SQLITE_PATH = os.environ.get(
    "MEMORY_SQLITE_PATH", os.path.expanduser("~/.mnemosyne/mnemosyne.db")
)


class SQLiteStore(MemoryStore):
    """
    SQLite-backed store with JSON-encoded embeddings.
    Full v3.0 feature parity: Wing/Room scoping, timeline, versioning,
    RRF hybrid search, and temporal decay.
    """

    def __init__(self, db_path: str = SQLITE_PATH) -> None:
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        """Get a new SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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
            # Ensure new columns exist on legacy tables
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(notes);")
            columns = [row["name"] for row in cur.fetchall()]
            if "wing" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN wing TEXT NOT NULL DEFAULT 'general';")
            if "room" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN room TEXT NOT NULL DEFAULT 'general';")
            if "last_accessed_at" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN last_accessed_at TEXT NOT NULL DEFAULT '';")
            conn.commit()

    def _archive_version(self, cur, title: str, vault_path: str):
        cur.execute("SELECT id, content, tags, salience FROM notes WHERE title = ? AND vault_path = ?;", (title, vault_path))
        row = cur.fetchone()
        if row:
            cur.execute(
                "INSERT INTO note_versions (note_id, title, content, tags, salience) VALUES (?, ?, ?, ?, ?);",
                (row["id"], title, row["content"], row["tags"], row["salience"]),
            )

    def log_timeline(self, action: str, note_title: Optional[str] = None, query: Optional[str] = None, summary: Optional[str] = None):
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO timeline (action, note_title, query, summary) VALUES (?, ?, ?, ?);",
                    (action, note_title, query, summary),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to log timeline event: {e}")

    def get_timeline(self, limit: int = 20) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, action as operation, note_title as title, query, summary, created_at FROM timeline ORDER BY id DESC LIMIT ?;", (limit,))
            return [dict(row) for row in cur.fetchall()]

    def get_note_history(self, title: str, limit: int = 10) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT nv.id, nv.title, SUBSTR(nv.content, 1, 200) as preview, nv.tags, nv.salience, nv.version_at
                   FROM note_versions nv
                   JOIN notes n ON nv.note_id = n.id
                   WHERE n.title = ?
                   ORDER BY nv.id DESC LIMIT ?;""",
                (title, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def upsert_note(
        self,
        title: str,
        content: str,
        tags: List[str],
        note_type: str,
        status: str,
        salience: float,
        embedding: List[float],
        vault_path: str,
        wing: str = "general",
        room: str = "general",
    ) -> str:
        with self._conn() as conn:
            cur = conn.cursor()
            self._archive_version(cur, title, vault_path)
            note_id = str(uuid.uuid4())
            emb_json = json.dumps(embedding)
            tags_json = json.dumps(tags)

            cur.execute(
                """
                INSERT INTO notes (
                    id, title, content, tags, note_type, status,
                    salience, embedding, vault_path, wing, room, last_accessed_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(title, vault_path) DO UPDATE SET
                    content = excluded.content,
                    tags = excluded.tags,
                    note_type = excluded.note_type,
                    status = excluded.status,
                    salience = excluded.salience,
                    embedding = excluded.embedding,
                    wing = excluded.wing,
                    room = excluded.room,
                    last_accessed_at = datetime('now'),
                    updated_at = datetime('now');
            """,
                (
                    note_id,
                    title,
                    content,
                    tags_json,
                    note_type,
                    status,
                    salience,
                    emb_json,
                    vault_path,
                    wing,
                    room,
                ),
            )
            cur.execute("SELECT id FROM notes WHERE title = ? AND vault_path = ?;", (title, vault_path))
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else note_id

    def delete_note(self, title: str, vault_path: str) -> bool:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM notes WHERE title = ? AND vault_path = ?;", (title, vault_path))
            conn.commit()
            return cur.rowcount > 0

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search_semantic(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
        scope: Optional[Dict] = None,
    ) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            query_sql = "SELECT id, title, content, tags, note_type, salience, vault_path, wing, room, embedding FROM notes WHERE status = 'active'"
            params = []

            if scope:
                if scope.get("wing"):
                    query_sql += " AND wing = ?"
                    params.append(scope["wing"])
                if scope.get("room"):
                    query_sql += " AND room = ?"
                    params.append(scope["room"])

            if filters:
                if filters.get("note_type"):
                    query_sql += " AND note_type = ?"
                    params.append(filters["note_type"])

            cur.execute(query_sql, params)
            rows = cur.fetchall()

            scored = []
            for row in rows:
                if not row["embedding"]:
                    continue
                emb = json.loads(row["embedding"])
                score = self._cosine_sim(query_embedding, emb)
                note_tags = json.loads(row["tags"]) if row["tags"] else []

                if filters and filters.get("tags"):
                    if not any(t in note_tags for t in filters["tags"]):
                        continue

                scored.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "content": row["content"],
                        "tags": note_tags,
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
            if results:
                ids = [r["id"] for r in results]
                placeholders = ",".join("?" for _ in ids)
                conn.execute(f"UPDATE notes SET last_accessed_at = datetime('now') WHERE id IN ({placeholders});", ids)
                conn.commit()
            return results

    def search_keyword(self, query: str, top_k: int = 10, scope: Optional[Dict] = None) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            query_sql = """
                SELECT id, title, content, tags, note_type, salience, vault_path, wing, room
                FROM notes
                WHERE status = 'active' AND (title LIKE ? OR content LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%"]

            if scope:
                if scope.get("wing"):
                    query_sql += " AND wing = ?"
                    params.append(scope["wing"])
                if scope.get("room"):
                    query_sql += " AND room = ?"
                    params.append(scope["room"])

            query_sql += " ORDER BY salience DESC LIMIT ?;"
            params.append(top_k)

            cur.execute(query_sql, params)
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
                conn.commit()
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

            conn.commit()
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
                        INSERT INTO links (id, source_note_id, target_note_id, link_type)
                        VALUES (?, ?, ?, 'wiki')
                        ON CONFLICT (source_note_id, target_note_id) DO NOTHING;
                    """,
                        (link_id, note_id, target["id"]),
                    )
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM notes WHERE status = 'active';")
            notes = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM links;")
            links = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM prospective WHERE status = 'pending';")
            pending = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM timeline;")
            timeline_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM note_versions;")
            version_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM notes WHERE status = 'archived';")
            archived = cur.fetchone()[0]
            cur.execute("SELECT DISTINCT wing FROM notes WHERE status = 'active';")
            wings = [r[0] for r in cur.fetchall()]
            return {
                "notes": notes,
                "links": links,
                "pending_reminders": pending,
                "timeline_entries": timeline_count,
                "versions": version_count,
                "archived": archived,
                "wings": wings,
                "version": "3.0",
            }
