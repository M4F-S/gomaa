"""SQLite store with pure-Python vector similarity."""

import os
import json
import math
import logging
import sqlite3
import uuid
from typing import List, Dict, Optional

from mnemosyne.stores.base import MemoryStore

logger = logging.getLogger("unified-memory")

SQLITE_PATH = os.environ.get(
    "MEMORY_SQLITE_PATH", os.path.expanduser("~/.mnemosyne/mnemosyne.db")
)


class SQLiteStore(MemoryStore):
    """
    SQLite-backed store with JSON-encoded embeddings.
    Semantic search uses brute-force cosine similarity in Python.
    Good for <10K notes (fast enough for early users).
    """

    def __init__(self, db_path: str = SQLITE_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        """Get a new SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
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
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(title, vault_path)
                );

                CREATE TABLE IF NOT EXISTS links (
                    id TEXT PRIMARY KEY,
                    source_note_id TEXT NOT NULL
                        REFERENCES notes(id) ON DELETE CASCADE,
                    target_note_id TEXT NOT NULL
                        REFERENCES notes(id) ON DELETE CASCADE,
                    link_type TEXT DEFAULT 'wiki',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(source_note_id, target_note_id)
                );

                CREATE TABLE IF NOT EXISTS prospective (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    trigger_at TEXT NOT NULL,
                    recurring TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS notes_status_idx ON notes(status);
                CREATE INDEX IF NOT EXISTS notes_type_idx ON notes(note_type);
                CREATE INDEX IF NOT EXISTS prospective_trigger_idx
                    ON prospective(trigger_at);
                """
            )
            conn.commit()
            logger.info("SQLite schema initialized.")

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
    ) -> str:
        """Insert or update a note."""
        note_id = str(uuid.uuid4())
        with self._conn() as conn:
            # Check if note exists
            row = conn.execute(
                "SELECT id FROM notes WHERE title = ? AND vault_path = ?",
                (title, vault_path),
            ).fetchone()
            if row:
                note_id = row["id"]
                conn.execute(
                    """
                    UPDATE notes SET
                        content = ?, tags = ?, note_type = ?, status = ?,
                        salience = ?, embedding = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """,
                    (
                        content,
                        json.dumps(tags),
                        note_type,
                        status,
                        salience,
                        json.dumps(embedding),
                        note_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO notes (
                        id, title, content, tags, note_type,
                        status, salience, embedding, vault_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        note_id,
                        title,
                        content,
                        json.dumps(tags),
                        note_type,
                        status,
                        salience,
                        json.dumps(embedding),
                        vault_path,
                    ),
                )
            conn.commit()
            return note_id

    def delete_note(self, title: str, vault_path: str) -> bool:
        """Delete a note."""
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM notes WHERE title = ? AND vault_path = ?",
                (title, vault_path),
            )
            conn.commit()
            return bool(cur.rowcount > 0)

    def search_semantic(
        self, query_embedding: List[float], top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Brute-force cosine similarity in Python."""
        with self._conn() as conn:
            where = "status = 'active'"
            params: List[str] = []
            if filters:
                if filters.get("note_type"):
                    where += " AND note_type = ?"
                    params.append(filters["note_type"])
            rows = conn.execute(
                f"SELECT * FROM notes WHERE {where}", params
            ).fetchall()

        results = []
        for row in rows:
            emb = json.loads(row["embedding"] or "[]")
            if not emb:
                continue
            score = self._cosine_similarity(query_embedding, emb)
            results.append({**dict(row), "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def search_keyword(self, query: str, top_k: int = 10) -> List[Dict]:
        """Simple substring search (SQLite has no native full-text)."""
        terms = query.lower().split()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM notes WHERE status = 'active'"
            ).fetchall()

        results = []
        for row in rows:
            text = (row["title"] + " " + row["content"]).lower()
            score = (
                sum(1 for term in terms if term in text) / len(terms)
                if terms else 0
            )
            if score > 0:
                results.append({**dict(row), "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def search_graph(self, note_title: str, depth: int = 2,
                     top_k: int = 10) -> List[Dict]:
        """BFS graph traversal via wiki-links."""
        with self._conn() as conn:
            # Find starting note
            start = conn.execute(
                "SELECT id FROM notes WHERE title = ? AND status = 'active'",
                (note_title,),
            ).fetchone()
            if not start:
                return []

            visited = set()
            queue = [(start["id"], 0)]
            results = []

            while queue:
                nid, d = queue.pop(0)
                if nid in visited or d >= depth:
                    continue
                visited.add(nid)

                # Find neighbors
                neighbors = conn.execute(
                    """
                    SELECT n.* FROM notes n
                    JOIN links l ON l.target_note_id = n.id
                    WHERE l.source_note_id = ? AND n.status = 'active'
                """,
                    (nid,),
                ).fetchall()

                for neighbor in neighbors:
                    if neighbor["id"] not in visited:
                        results.append({**dict(neighbor), "depth": d + 1})
                        queue.append((neighbor["id"], d + 1))

            # Sort by depth then salience
            results.sort(key=lambda x: (x["depth"], -x.get("salience", 0)))
            return results[:top_k]

    def hybrid_search(
        self, query: str, query_embedding: List[float], top_k: int = 10
    ) -> List[Dict]:
        """RRF of semantic + keyword + salience."""
        semantic = self.search_semantic(query_embedding, top_k=top_k * 2)
        keyword = self.search_keyword(query, top_k=top_k * 2)

        scores: Dict[str, Dict] = {}

        def add_results(
            results: List[Dict], source: str, weight: float
        ) -> None:
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

        sorted_results = sorted(
            scores.values(), key=lambda x: x["rrf_score"], reverse=True
        )
        return sorted_results[:top_k]

    def update_links(self, note_id: str, wiki_links: List[str]) -> None:
        """Update graph edges."""
        with self._conn() as conn:
            conn.execute("DELETE FROM links WHERE source_note_id = ?",
                         (note_id,))
            for target_title in wiki_links:
                target = conn.execute(
                    "SELECT id FROM notes WHERE title = ? AND status = 'active'",
                    (target_title.strip(),),
                ).fetchone()
                if target:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO links (
                            id, source_note_id, target_note_id, link_type
                        )
                        VALUES (?, ?, ?, 'wiki')
                    """,
                        (str(uuid.uuid4()), note_id, target["id"]),
                    )
            conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """Get vault statistics."""
        with self._conn() as conn:
            note_count = conn.execute(
                "SELECT COUNT(*) FROM notes WHERE status = 'active'"
            ).fetchone()[0]
            link_count = conn.execute(
                "SELECT COUNT(*) FROM links"
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM prospective WHERE status = 'pending'"
            ).fetchone()[0]
            return {"notes": note_count, "links": link_count,
                    "pending_reminders": pending}

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
