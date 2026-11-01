import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base import MemoryStore

logger = logging.getLogger("gomaa-sqlite")


class SQLiteStore(MemoryStore):
    def __init__(self, db_path: str = "gomaa.db"):
        self.db_path = os.path.expanduser(db_path)
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._ensure_schema()
        self._migrate_identity_key()
        # Stores created before the encoder tag existed need the column added in
        # place. SQLite has no ADD COLUMN IF NOT EXISTS, so a duplicate-column
        # error is the expected "already migrated" path.
        try:
            with self._conn() as conn:
                conn.execute("ALTER TABLE notes ADD COLUMN embedder_id TEXT")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise

    def _migrate_identity_key(self) -> bool:
        """Rebuild the notes table when it still carries the legacy
        UNIQUE(title, vault_path) key.

        SQLite cannot ALTER a constraint, so the table is rebuilt around the same
        rows. This is the counterpart of the Postgres DO block: without it a
        4.0.0 database silently rewrites one wing's note when another wing writes
        the same title. Refuses (raise) when the rebuild would merge rows.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='notes'"
            ).fetchone()
            ddl = (row["sql"] if row else "") or ""
            if "UNIQUE(title, vault_path)" not in ddl:
                return False
            dup = conn.execute(
                "SELECT count(*) c FROM (SELECT 1 FROM notes "
                "GROUP BY wing, room, title HAVING count(*) > 1)"
            ).fetchone()["c"]
            if dup:
                raise RuntimeError(
                    f"notes is keyed on (title, vault_path) and holds {dup} duplicate "
                    "(wing, room, title) group(s); refusing to migrate and merge rows"
                )
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(notes)").fetchall()]
            collist = ", ".join(f'"{c}"' for c in cols)
            new_ddl = ddl.replace("UNIQUE(title, vault_path)", "UNIQUE(wing, room, title)")
            new_ddl = new_ddl.replace("CREATE TABLE notes", "CREATE TABLE notes_new", 1)
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("ALTER TABLE notes RENAME TO notes_legacy")
            conn.execute(new_ddl)
            conn.execute(f"INSERT INTO notes_new ({collist}) SELECT {collist} FROM notes_legacy")
            conn.execute("DROP TABLE notes_legacy")
            conn.execute("ALTER TABLE notes_new RENAME TO notes")
            conn.execute("PRAGMA foreign_keys=ON")
        logger.warning("notes: rebuilt with UNIQUE(wing, room, title) (legacy SQLite key)")
        return True

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
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
                    memory_type TEXT NOT NULL DEFAULT 'semantic',
                    episodic_parent_hash TEXT,
                    embedder_id TEXT,
                    superseded_by TEXT,
                    access_count INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 1.0,
                    last_accessed_at TEXT NOT NULL DEFAULT (datetime('now')),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(wing, room, title)
                );

                CREATE TABLE IF NOT EXISTS links (
                    id TEXT PRIMARY KEY,
                    source_note_id TEXT NOT NULL,
                    target_note_id TEXT NOT NULL,
                    link_type TEXT NOT NULL DEFAULT 'wiki',
                    relation_type TEXT NOT NULL DEFAULT 'associative',
                    edge_weight REAL DEFAULT 1.0,
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

                CREATE TABLE IF NOT EXISTS episodic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_uuid TEXT UNIQUE,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    origin_agent TEXT NOT NULL,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                    event_type TEXT NOT NULL,
                    stimulus TEXT NOT NULL,
                    response TEXT NOT NULL,
                    outcome_status TEXT DEFAULT 'success',
                    surprise_factor REAL DEFAULT 0.0,
                    content_hash TEXT NOT NULL,
                    consolidated INTEGER DEFAULT 0,
                    embedding TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_episodic_unconsolidated ON episodic_events (consolidated, timestamp);
                CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_events (session_id, turn_index);

                CREATE TABLE IF NOT EXISTS procedural_playbooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL UNIQUE,
                    domain TEXT NOT NULL,
                    description TEXT NOT NULL,
                    preconditions TEXT NOT NULL DEFAULT '[]',
                    tool_sequence TEXT NOT NULL DEFAULT '[]',
                    error_recovery TEXT NOT NULL DEFAULT '{}',
                    invocation_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    embedding TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_procedural_domain ON procedural_playbooks (domain);

                CREATE TABLE IF NOT EXISTS working_memory (
                    session_id TEXT PRIMARY KEY,
                    agent_role TEXT NOT NULL,
                    active_goal TEXT,
                    subtask_stack TEXT DEFAULT '[]',
                    hypotheses TEXT DEFAULT '[]',
                    attention_window TEXT DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS epistemic_conflicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    old_note_id TEXT,
                    new_note_id TEXT,
                    detected_at TEXT NOT NULL DEFAULT (datetime('now')),
                    conflict_description TEXT NOT NULL,
                    resolution_status TEXT DEFAULT 'pending',
                    resolved_by TEXT
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
            if "memory_type" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN memory_type TEXT NOT NULL DEFAULT 'semantic';")
            if "episodic_parent_hash" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN episodic_parent_hash TEXT;")
            if "superseded_by" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN superseded_by TEXT;")
            if "access_count" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN access_count INTEGER DEFAULT 0;")
            if "confidence" not in columns:
                cur.execute("ALTER TABLE notes ADD COLUMN confidence REAL DEFAULT 1.0;")

            cur.execute("PRAGMA table_info(links);")
            link_columns = [row["name"] for row in cur.fetchall()]
            if "relation_type" not in link_columns:
                cur.execute("ALTER TABLE links ADD COLUMN relation_type TEXT NOT NULL DEFAULT 'associative';")
            if "edge_weight" not in link_columns:
                cur.execute("ALTER TABLE links ADD COLUMN edge_weight REAL DEFAULT 1.0;")

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

    def log_timeline(
        self, action: str, note_title: Optional[str] = None, query: Optional[str] = None, summary: Optional[str] = None
    ) -> None:
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

    def scopes_for_title(self, title: str) -> List[Tuple[str, str]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT wing, room FROM notes WHERE title = ?", (title,))
            return [(r["wing"], r["room"]) for r in cur.fetchall()]

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
        memory_type: str = "semantic",
        episodic_parent_hash: Optional[str] = None,
        superseded_by: Optional[str] = None,
        confidence: float = 1.0,
        preserve_lifecycle: bool = False,
        embedder_id: Optional[str] = None,
    ) -> str:
        vault_path = str(vault_path)
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, content, tags, salience, access_count FROM notes "
                "WHERE title = ? AND wing = ? AND room = ? "
                "ORDER BY updated_at DESC LIMIT 1;",
                (title, wing, room),
            )
            existing = cur.fetchone()

            if existing and preserve_lifecycle:
                conn.execute(
                    """
                    UPDATE notes SET content = ?, tags = ?, wing = ?, room = ?,
                        embedding = COALESCE(?, embedding),
                        embedder_id = COALESCE(?, embedder_id),
                        updated_at = datetime('now')
                    WHERE id = ?;
                    """,
                    (
                        content,
                        json.dumps(tags),
                        wing,
                        room,
                        json.dumps(embedding) if embedding else None,
                        embedder_id,
                        existing["id"],
                    ),
                )
                note_id = existing["id"]
            elif existing:
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
                        embedding = COALESCE(?, embedding),
                        embedder_id = COALESCE(?, embedder_id), wing = ?, room = ?, origin_agent = ?,
                        memory_type = ?, episodic_parent_hash = ?, superseded_by = ?, confidence = ?,
                        access_count = access_count + 1,
                        last_accessed_at = datetime('now'), updated_at = datetime('now')
                    WHERE id = ?;
                """,
                    (
                        content,
                        json.dumps(tags),
                        note_type,
                        status,
                        salience,
                        json.dumps(embedding) if embedding else None,
                        embedder_id,
                        wing,
                        room,
                        origin_agent,
                        memory_type,
                        episodic_parent_hash,
                        superseded_by,
                        confidence,
                        note_id,
                    ),
                )
            else:
                note_id = str(uuid.uuid4())
                try:
                    conn.execute(
                        """
                        INSERT INTO notes (
                            id, title, content, tags, note_type, status, salience,
                            embedding, vault_path, wing, room, origin_agent,
                            memory_type, episodic_parent_hash, superseded_by, confidence,
                            embedder_id, access_count, last_accessed_at, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'), datetime('now'));
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
                            memory_type,
                            episodic_parent_hash,
                            superseded_by,
                            confidence,
                            embedder_id,
                        ),
                    )
                except sqlite3.IntegrityError:
                    # Re-select by the identity the table is supposed to be keyed
                    # on. Selecting by (title, vault_path) retargeted a cross-scope
                    # write onto another wing's row and silently overwrote it.
                    cur.execute(
                        "SELECT id FROM notes WHERE title = ? AND wing = ? AND room = ?;",
                        (title, wing, room),
                    )
                    existing = cur.fetchone()
                    if existing:
                        note_id = existing["id"]
                    else:
                        raise RuntimeError(
                            f"upsert_note: integrity error for {title!r} in {wing}/{room} "
                            "and no matching row exists; refusing to return an unwritten id "
                            "(the notes table is probably still keyed on the legacy "
                            "(title, vault_path) constraint)"
                        )
                        conn.execute(
                            """
                            UPDATE notes
                            SET content = ?, tags = ?, note_type = ?, status = ?, salience = ?,
                                embedding = COALESCE(?, embedding),
                                embedder_id = COALESCE(?, embedder_id), wing = ?, room = ?, origin_agent = ?,
                                memory_type = ?, episodic_parent_hash = ?, superseded_by = ?, confidence = ?,
                                access_count = access_count + 1,
                                last_accessed_at = datetime('now'), updated_at = datetime('now')
                            WHERE id = ?;
                        """,
                            (
                                content,
                                json.dumps(tags),
                                note_type,
                                status,
                                salience,
                                json.dumps(embedding) if embedding else None,
                                embedder_id,
                                wing,
                                room,
                                origin_agent,
                                memory_type,
                                episodic_parent_hash,
                                superseded_by,
                                confidence,
                                note_id,
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

    def delete_note(
        self,
        title: str,
        vault_path: str = "",
        wing: Optional[str] = None,
        room: Optional[str] = None,
    ) -> bool:
        vault_path = str(vault_path)
        sql = "DELETE FROM notes WHERE title = ?"
        params: List[Any] = [title]
        if wing is not None:
            sql += " AND wing = ?"
            params.append(wing)
        if room is not None:
            sql += " AND room = ?"
            params.append(room)
        if wing is None and room is None:
            sql += " AND vault_path = ?"
            params.append(vault_path)
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            return cur.rowcount > 0

    def _listing_where(self, scope, status):
        where, params = "WHERE 1=1", []
        if status:
            where += " AND status = ?"
            params.append(status)
        scope_clause, scope_params = self._scope_clause(scope)
        if scope_clause:
            where += " AND " + scope_clause
            params.extend(scope_params)
        return where, params

    def list_notes(self, limit=100, offset=0, scope=None, status="active"):
        where, params = self._listing_where(scope, status)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, content, tags, note_type, salience, vault_path, wing, room, "
                "access_count, confidence, created_at, updated_at FROM notes "
                f"{where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                (*params, int(limit), int(offset)),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
            d["pinned"] = "pinned" in [t.lower() for t in d["tags"]]
            out.append(d)
        return out

    def count_notes(self, scope=None, status="active"):
        where, params = self._listing_where(scope, status)
        with self._conn() as conn:
            return conn.execute(f"SELECT COUNT(*) c FROM notes {where}", params).fetchone()["c"]

    def count_by_wing_room(self, status="active"):
        where, params = self._listing_where(None, status)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT wing, room, COUNT(*) c FROM notes {where} GROUP BY wing, room ORDER BY c DESC",
                params,
            ).fetchall()
        return [{"wing": r["wing"], "room": r["room"], "count": r["c"]} for r in rows]

    def search_semantic(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
        scope: Optional[Dict] = None,
        embedder_id: Optional[str] = None,
    ) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            where = "WHERE status = 'active' AND embedding IS NOT NULL"
            params = []
            if embedder_id:
                # Same rule as the Postgres store: never rank hash-fallback noise
                # against a real query vector. NULL rows stay visible.
                where += " AND (embedder_id IS NULL OR embedder_id = ?)"
                params.append(embedder_id)

            scope_clause, scope_params = self._scope_clause(scope)
            if scope_clause:
                where += " AND " + scope_clause
                params.extend(scope_params)

            if filters:
                if filters.get("note_type"):
                    where += " AND note_type = ?"
                    params.append(filters["note_type"])

            cur.execute(
                f"SELECT id, title, content, tags, note_type, salience, vault_path, wing, room, embedding, memory_type, episodic_parent_hash, superseded_by, access_count, confidence FROM notes {where};",
                params,
            )
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
                        "memory_type": row["memory_type"] if "memory_type" in row.keys() else "semantic",
                        "episodic_parent_hash": row["episodic_parent_hash"] if "episodic_parent_hash" in row.keys() else None,
                        "superseded_by": row["superseded_by"] if "superseded_by" in row.keys() else None,
                        "access_count": row["access_count"] if "access_count" in row.keys() else 0,
                        "confidence": row["confidence"] if "confidence" in row.keys() else 1.0,
                    }
                )

            scored.sort(key=lambda x: x["score"], reverse=True)
            results = scored[:top_k]

            high_conf = [r["id"] for r in results if r["score"] >= 0.55]
            if high_conf:
                placeholders = ",".join("?" for _ in high_conf)
                conn.execute(
                    f"UPDATE notes SET last_accessed_at = datetime('now'), access_count = COALESCE(access_count, 0) + 1 WHERE id IN ({placeholders});",
                    high_conf,
                )

            return results

    def search_keyword(self, query: str, top_k: int = 10, scope: Optional[Dict] = None) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            words = [w for w in re.split(r"\s+", query) if w and len(w) > 1 and w not in ("!", "&", "|", ":")]
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
                SELECT id, title, content, tags, note_type, salience, vault_path, wing, room,
                       memory_type, episodic_parent_hash, superseded_by, access_count, confidence
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
                        "memory_type": row["memory_type"] if "memory_type" in row.keys() else "semantic",
                        "episodic_parent_hash": row["episodic_parent_hash"] if "episodic_parent_hash" in row.keys() else None,
                        "superseded_by": row["superseded_by"] if "superseded_by" in row.keys() else None,
                        "access_count": row["access_count"] if "access_count" in row.keys() else 0,
                        "confidence": row["confidence"] if "confidence" in row.keys() else 1.0,
                    }
                )
            if results:
                ids = [r["id"] for r in results]
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"UPDATE notes SET last_accessed_at = datetime('now'), access_count = COALESCE(access_count, 0) + 1 WHERE id IN ({placeholders});",
                    ids,
                )
            return results

    def search_graph(
        self,
        note_title: str,
        depth: int = 2,
        top_k: int = 10,
        scope: Optional[Dict] = None,
    ) -> List[Dict]:
        # Graph walking crosses wings by design; scope must be enforced on both
        # the seed and the neighbours, or a beta note answers an alpha query.
        seed_scope, seed_args = "", []
        nbr_scope, nbr_args = "", []
        if scope:
            if scope.get("wing"):
                seed_scope += " AND wing = ?"
                nbr_scope += " AND n.wing = ?"
                seed_args.append(scope["wing"])
                nbr_args.append(scope["wing"])
            if scope.get("room"):
                seed_scope += " AND room = ?"
                nbr_scope += " AND n.room = ?"
                seed_args.append(scope["room"])
                nbr_args.append(scope["room"])

        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM notes WHERE title = ? AND status = 'active'" + seed_scope + ";",
                (note_title, *seed_args),
            )
            root = cur.fetchone()
            if not root:
                cur.execute(
                    "SELECT id FROM notes WHERE title LIKE ? AND status = 'active'"
                    + seed_scope
                    + " ORDER BY salience DESC LIMIT 1;",
                    (f"%{note_title}%", *seed_args),
                )
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
                        JOIN notes n ON (CASE WHEN l.source_note_id = ? THEN n.id = l.target_note_id ELSE n.id = l.source_note_id END)
                        WHERE (l.source_note_id = ? OR l.target_note_id = ?) AND n.status = 'active'
                        """
                        + nbr_scope
                        + ";",
                        (nid, nid, nid, *nbr_args),
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

    def search_associative_ppr(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        scope: Optional[Dict] = None,
        restart_prob: float = 0.15,
        embedder_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        HippoRAG 2 Personalized PageRank associative search.
        Seeds nodes from dense vector similarity, diffusing activation across graph topology.
        """
        seeds = self.search_semantic(
            query_embedding, top_k=5, scope=scope, embedder_id=embedder_id
        )
        if not seeds:
            return []

        seed_scores = {r["title"]: max(0.01, float(r.get("score", 0.5))) for r in seeds}
        adj = self.get_graph_adjacency()

        from gomaa.hipporag import HippoRAGEngine

        engine = HippoRAGEngine(restart_prob=restart_prob)
        ppr_distribution = engine.compute_ppr(adj, seed_scores)

        sorted_nodes = sorted(ppr_distribution.items(), key=lambda x: x[1], reverse=True)[:top_k]
        if not sorted_nodes:
            return []

        titles = [n[0] for n in sorted_nodes]
        score_map = dict(sorted_nodes)

        # Scope must be enforced at fetch time, not only on the seeds: PPR
        # diffuses across the whole graph, so an unscoped fetch returns another
        # wing's notes to a scoped caller (measured).
        scope_sql, scope_args = "", []
        if scope:
            if scope.get("wing"):
                scope_sql += " AND wing = ?"
                scope_args.append(scope["wing"])
            if scope.get("room"):
                scope_sql += " AND room = ?"
                scope_args.append(scope["room"])

        with self._conn() as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in titles)
            cur.execute(
                f"""
                SELECT id, title, content, tags, note_type, salience, vault_path, wing, room, access_count, confidence
                FROM notes
                WHERE title IN ({placeholders}) AND status = 'active'{scope_sql};
            """,
                (*titles, *scope_args),
            )
            # Group by title instead of overwriting: with the scope key two
            # notes may legitimately share a title, and a title-keyed dict was
            # silently dropping all but the last one.
            by_title = {}
            for row in cur.fetchall():
                d = dict(row)
                d["tags"] = json.loads(d["tags"]) if d["tags"] else []
                d["ppr_score"] = score_map.get(d["title"], 0.0)
                d["score"] = d["ppr_score"]
                by_title.setdefault(d["title"], []).append(d)

            results = []
            for t in titles:
                results.extend(by_title.get(t, []))
            return results

    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        scope: Optional[Dict] = None,
        embedder_id: Optional[str] = None,
    ) -> List[Dict]:
        semantic = self.search_semantic(
            query_embedding, top_k=top_k * 2, scope=scope, embedder_id=embedder_id
        )
        keyword = self.search_keyword(query, top_k=top_k * 2, scope=scope)
        ppr_results = self.search_associative_ppr(query_embedding, top_k=top_k * 2, scope=scope)

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
        add_results(ppr_results, "hipporag_ppr", 1.2)

        for nid in scores:
            salience = scores[nid].get("salience", 0.5)
            access_count = scores[nid].get("access_count", 0)
            confidence = scores[nid].get("confidence", 1.0)
            # ACT-R dynamic activation bonus: frequency + salience + confidence
            actr_bonus = 0.005 * salience + 0.002 * math.log(1 + max(0, access_count)) * confidence
            scores[nid]["rrf_score"] += actr_bonus

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

            to_archive = []
            to_decay = []

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
                    new_salience = row["salience"] * decay_rate
                    if new_salience < archive_threshold:
                        to_archive.append((new_salience, row["id"]))
                    else:
                        to_decay.append((new_salience, row["id"]))

            if to_archive:
                cur.executemany("UPDATE notes SET status = 'archived', salience = ? WHERE id = ?;", to_archive)
                archived_count = len(to_archive)
            if to_decay:
                cur.executemany("UPDATE notes SET salience = ? WHERE id = ?;", to_decay)
                decayed_count = len(to_decay)

            return {"decayed": decayed_count, "archived": archived_count}

    def archive_stale(self, archive_threshold: float = 0.10, days: int = 90) -> int:
        """Archive notes not updated in N days with salience below threshold."""
        now = datetime.now(timezone.utc)
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, salience, tags, updated_at FROM notes WHERE status = 'active';")
            rows = cur.fetchall()
            to_archive_ids = []
            for row in rows:
                tags = json.loads(row["tags"]) if row["tags"] else []
                if any(t in tags for t in ["pinned", "permanent", "core"]) or row["salience"] >= 1.0:
                    continue
                upd_str = row["updated_at"]
                try:
                    upd_dt = datetime.fromisoformat(upd_str.replace("Z", "+00:00"))
                    if upd_dt.tzinfo is None:
                        upd_dt = upd_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    upd_dt = now
                days_elapsed = (now - upd_dt).total_seconds() / 86400.0
                if days_elapsed >= days and row["salience"] < archive_threshold:
                    to_archive_ids.append((row["id"],))

            if to_archive_ids:
                cur.executemany("UPDATE notes SET status = 'archived' WHERE id = ?;", to_archive_ids)
            return len(to_archive_ids)

    def update_links(self, note_id: str, wiki_links: List[str]) -> None:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM links WHERE source_note_id = ?;", (note_id,))
            if wiki_links:
                link_rows = []
                for target_title in wiki_links:
                    cur.execute("SELECT id FROM notes WHERE title = ? AND status = 'active';", (target_title.strip(),))
                    target = cur.fetchone()
                    if target:
                        link_rows.append((str(uuid.uuid4()), note_id, target["id"]))
                if link_rows:
                    cur.executemany(
                        "INSERT OR IGNORE INTO links (id, source_note_id, target_note_id, link_type) VALUES (?, ?, ?, 'wiki');",
                        link_rows,
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

    # --- Prospective-reminder support (SQLite-portable) ---
    # The standalone ProspectiveMemory class uses PG-only syntax (%s, RETURNING,
    # NOW() + INTERVAL). These store native methods let the core schedule reminders
    # on the SQLite backend. Kept in the store so ProspectiveMemory can delegate
    # to whatever backend is active.

    def schedule_reminder(self, title: str, content: str, trigger_at: str, recurring: Optional[str] = None) -> str:
        """Insert a pending reminder, returning its id string."""
        rid = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO prospective (id, title, content, trigger_at, recurring, status) "
                "VALUES (?, ?, ?, ?, ?, 'pending');",
                (rid, title, content, trigger_at, recurring),
            )
        return rid

    def get_due_reminders(self, window_hours: int = 24) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            # Due = pending AND trigger_at <= now + window.
            # trigger_at is stored as ISO with a 'T' separator (e.g.
            # '2026-08-25T09:00:00') while SQLite datetime('now', ...) emits a
            # space separator. Normalize with replace() so the string compare is
            # correct even for same-day triggers ('T' sorts AFTER ' ').
            cur.execute(
                "SELECT id, title, content, trigger_at, recurring FROM prospective "
                "WHERE status = 'pending' "
                "AND replace(trigger_at, 'T', ' ') <= datetime('now', ?) "
                "ORDER BY trigger_at;",
                (f"+{int(window_hours)} hours",),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def mark_reminder_done(self, reminder_id: str) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE prospective SET status = 'done' WHERE id = ?;", (reminder_id,))

    # =========================================================================
    # Quadrant 1: Episodic Event Ledger
    # =========================================================================

    def log_episodic_event(
        self,
        session_id: str,
        turn_index: int,
        origin_agent: str,
        event_type: str,
        stimulus: str,
        response: str,
        outcome_status: str = "success",
        surprise_factor: float = 0.0,
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        event_uuid = str(uuid.uuid4())
        raw_to_hash = f"{session_id}:{turn_index}:{stimulus}:{response}".encode("utf-8")
        content_hash = hashlib.sha256(raw_to_hash).hexdigest()
        emb_json = json.dumps(embedding) if embedding else None

        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO episodic_events (
                    event_uuid, session_id, turn_index, origin_agent,
                    event_type, stimulus, response, outcome_status,
                    surprise_factor, content_hash, consolidated, embedding, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, datetime('now'));
            """,
                (
                    event_uuid,
                    session_id,
                    turn_index,
                    origin_agent,
                    event_type,
                    stimulus,
                    response,
                    outcome_status,
                    surprise_factor,
                    content_hash,
                    emb_json,
                ),
            )
            event_id = cur.lastrowid
            return {
                "id": event_id,
                "event_uuid": event_uuid,
                "session_id": session_id,
                "turn_index": turn_index,
                "content_hash": content_hash,
                "consolidated": False,
            }

    def get_unconsolidated_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_uuid, session_id, turn_index, origin_agent,
                       timestamp, event_type, stimulus, response, outcome_status,
                       surprise_factor, content_hash, consolidated, embedding
                FROM episodic_events
                WHERE consolidated = 0
                ORDER BY timestamp ASC
                LIMIT ?;
            """,
                (limit,),
            )
            results = []
            for row in cur.fetchall():
                d = dict(row)
                d["embedding"] = json.loads(d["embedding"]) if d["embedding"] else None
                d["consolidated"] = bool(d["consolidated"])
                results.append(d)
            return results

    def mark_events_consolidated(self, event_ids: List[Any]) -> int:
        if not event_ids:
            return 0
        with self._conn() as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in event_ids)
            cur.execute(
                f"UPDATE episodic_events SET consolidated = 1 WHERE id IN ({placeholders});",
                event_ids,
            )
            return cur.rowcount

    def get_episodic_events(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            if session_id:
                cur.execute(
                    """
                    SELECT id, event_uuid, session_id, turn_index, origin_agent,
                           timestamp, event_type, stimulus, response, outcome_status,
                           surprise_factor, content_hash, consolidated, embedding
                    FROM episodic_events
                    WHERE session_id = ?
                    ORDER BY turn_index ASC, timestamp ASC
                    LIMIT ?;
                """,
                    (session_id, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, event_uuid, session_id, turn_index, origin_agent,
                           timestamp, event_type, stimulus, response, outcome_status,
                           surprise_factor, content_hash, consolidated, embedding
                    FROM episodic_events
                    ORDER BY timestamp DESC
                    LIMIT ?;
                """,
                    (limit,),
                )
            results = []
            for row in cur.fetchall():
                d = dict(row)
                d["embedding"] = json.loads(d["embedding"]) if d["embedding"] else None
                d["consolidated"] = bool(d["consolidated"])
                results.append(d)
            return results

    # =========================================================================
    # Quadrant 2: Procedural Playbooks
    # =========================================================================

    def upsert_playbook(
        self,
        skill_name: str,
        domain: str,
        description: str,
        preconditions: List[Any],
        tool_sequence: List[Any],
        error_recovery: Dict[str, Any],
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        precond_json = json.dumps(preconditions)
        tool_seq_json = json.dumps(tool_sequence)
        recovery_json = json.dumps(error_recovery)
        emb_json = json.dumps(embedding) if embedding else None

        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, invocation_count, success_count FROM procedural_playbooks WHERE skill_name = ?;", (skill_name,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE procedural_playbooks
                    SET domain = ?, description = ?, preconditions = ?, tool_sequence = ?,
                        error_recovery = ?, embedding = COALESCE(?, embedding), updated_at = datetime('now')
                    WHERE skill_name = ?;
                """,
                    (domain, description, precond_json, tool_seq_json, recovery_json, emb_json, skill_name),
                )
                pid = existing["id"]
                inv = existing["invocation_count"]
                succ = existing["success_count"]
            else:
                cur.execute(
                    """
                    INSERT INTO procedural_playbooks (
                        skill_name, domain, description, preconditions, tool_sequence,
                        error_recovery, invocation_count, success_count, embedding, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, datetime('now'), datetime('now'));
                """,
                    (skill_name, domain, description, precond_json, tool_seq_json, recovery_json, emb_json),
                )
                pid = cur.lastrowid
                inv, succ = 0, 0

            bayesian_rate = (succ + 1.0) / (inv + 2.0)
            return {
                "id": pid,
                "skill_name": skill_name,
                "domain": domain,
                "bayesian_success_rate": bayesian_rate,
            }

    def search_playbooks(
        self,
        query_embedding: Optional[List[float]] = None,
        domain: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            query = "SELECT id, skill_name, domain, description, preconditions, tool_sequence, error_recovery, invocation_count, success_count, embedding FROM procedural_playbooks"
            params: List[Any] = []
            if domain:
                query += " WHERE domain = ?"
                params.append(domain)

            cur.execute(query, params)
            rows = cur.fetchall()
            playbooks = []
            for row in rows:
                p = dict(row)
                p["preconditions"] = json.loads(p["preconditions"]) if p["preconditions"] else []
                p["tool_sequence"] = json.loads(p["tool_sequence"]) if p["tool_sequence"] else []
                p["error_recovery"] = json.loads(p["error_recovery"]) if p["error_recovery"] else {}
                emb = json.loads(p["embedding"]) if p["embedding"] else None
                p["embedding"] = emb
                p["bayesian_success_rate"] = (p["success_count"] + 1.0) / (p["invocation_count"] + 2.0)

                # Similarity scoring
                score = 0.0
                if query_embedding and emb:
                    dot = sum(a * b for a, b in zip(query_embedding, emb))
                    norm_q = sum(a * a for a in query_embedding) ** 0.5
                    norm_e = sum(b * b for b in emb) ** 0.5
                    score = dot / (norm_q * norm_e) if (norm_q > 0 and norm_e > 0) else 0.0
                p["score"] = score
                playbooks.append(p)

            if query_embedding:
                playbooks.sort(key=lambda x: (x["score"] * 0.7 + x["bayesian_success_rate"] * 0.3), reverse=True)
            else:
                playbooks.sort(key=lambda x: x["bayesian_success_rate"], reverse=True)

            return playbooks[:limit]

    def record_playbook_execution(self, skill_name: str, success: bool) -> bool:
        with self._conn() as conn:
            cur = conn.cursor()
            succ_inc = 1 if success else 0
            cur.execute(
                """
                UPDATE procedural_playbooks
                SET invocation_count = invocation_count + 1,
                    success_count = success_count + ?,
                    updated_at = datetime('now')
                WHERE skill_name = ?;
            """,
                (succ_inc, skill_name),
            )
            return cur.rowcount > 0

    def get_playbook(self, skill_name: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, skill_name, domain, description, preconditions, tool_sequence,
                       error_recovery, invocation_count, success_count, embedding
                FROM procedural_playbooks
                WHERE skill_name = ?;
            """,
                (skill_name,),
            )
            row = cur.fetchone()
            if not row:
                return None
            p = dict(row)
            p["preconditions"] = json.loads(p["preconditions"]) if p["preconditions"] else []
            p["tool_sequence"] = json.loads(p["tool_sequence"]) if p["tool_sequence"] else []
            p["error_recovery"] = json.loads(p["error_recovery"]) if p["error_recovery"] else {}
            p["embedding"] = json.loads(p["embedding"]) if p["embedding"] else None
            p["bayesian_success_rate"] = (p["success_count"] + 1.0) / (p["invocation_count"] + 2.0)
            return p

    # =========================================================================
    # Quadrant 3: Working Memory Buffer
    # =========================================================================

    def get_working_memory(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT session_id, agent_role, active_goal, subtask_stack, hypotheses, attention_window, updated_at
                FROM working_memory
                WHERE session_id = ?;
            """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            w = dict(row)
            w["subtask_stack"] = json.loads(w["subtask_stack"]) if w["subtask_stack"] else []
            w["hypotheses"] = json.loads(w["hypotheses"]) if w["hypotheses"] else []
            w["attention_window"] = json.loads(w["attention_window"]) if w["attention_window"] else []
            return w

    def update_working_memory(
        self,
        session_id: str,
        agent_role: str,
        active_goal: Optional[str] = None,
        subtask_stack: Optional[List[Any]] = None,
        hypotheses: Optional[List[Any]] = None,
        attention_window: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        if attention_window is not None:
            # Miller's Law (7 +/- 2): bound attention window to maximum 9 items
            attention_window = list(attention_window)[:9]
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT active_goal, subtask_stack, hypotheses, attention_window FROM working_memory WHERE session_id = ?;", (session_id,))
            existing = cur.fetchone()

            goal_val = active_goal if active_goal is not None else (existing["active_goal"] if existing else None)
            subtask_val = json.dumps(subtask_stack) if subtask_stack is not None else (existing["subtask_stack"] if existing else "[]")
            hypo_val = json.dumps(hypotheses) if hypotheses is not None else (existing["hypotheses"] if existing else "[]")
            attn_val = json.dumps(attention_window) if attention_window is not None else (existing["attention_window"] if existing else "[]")

            cur.execute(
                """
                INSERT INTO working_memory (session_id, agent_role, active_goal, subtask_stack, hypotheses, attention_window, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(session_id) DO UPDATE SET
                    agent_role = excluded.agent_role,
                    active_goal = excluded.active_goal,
                    subtask_stack = excluded.subtask_stack,
                    hypotheses = excluded.hypotheses,
                    attention_window = excluded.attention_window,
                    updated_at = datetime('now');
            """,
                (session_id, agent_role, goal_val, subtask_val, hypo_val, attn_val),
            )
            return {
                "session_id": session_id,
                "agent_role": agent_role,
                "active_goal": goal_val,
                "subtask_stack": json.loads(subtask_val),
                "hypotheses": json.loads(hypo_val),
                "attention_window": json.loads(attn_val),
            }

    def clear_working_memory(self, session_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM working_memory WHERE session_id = ?;", (session_id,))
            return cur.rowcount > 0

    # =========================================================================
    # Weighted Graph Links & Graph Topology
    # =========================================================================

    def add_weighted_link(
        self,
        source_id: Any,
        target_id: Any,
        relation_type: str = "associative",
        weight: float = 1.0,
    ) -> bool:
        link_id = str(uuid.uuid4())
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO links (id, source_note_id, target_note_id, link_type, relation_type, edge_weight, created_at)
                VALUES (?, ?, ?, 'wiki', ?, ?, datetime('now'))
                ON CONFLICT(source_note_id, target_note_id) DO UPDATE SET
                    relation_type = excluded.relation_type,
                    edge_weight = excluded.edge_weight;
            """,
                (link_id, str(source_id), str(target_id), relation_type, float(weight)),
            )
            return True

    def get_graph_adjacency(self) -> Dict[str, List[Dict[str, Any]]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT ns.title AS source_title, nt.title AS target_title,
                       l.relation_type, l.edge_weight
                FROM links l
                JOIN notes ns ON ns.id = l.source_note_id
                JOIN notes nt ON nt.id = l.target_note_id
                WHERE ns.status = 'active' AND nt.status = 'active';
            """
            )
            adj: Dict[str, List[Dict[str, Any]]] = {}
            rows = cur.fetchall()
            for row in rows:
                src = row["source_title"]
                if src not in adj:
                    adj[src] = []
                adj[src].append({
                    "target_title": row["target_title"],
                    "relation_type": row["relation_type"],
                    "edge_weight": float(row["edge_weight"]),
                })
            for row in rows:
                src = row["source_title"]
                tgt = row["target_title"]
                if tgt not in adj:
                    adj[tgt] = []
                if not any(e["target_title"] == src for e in adj[tgt]):
                    adj[tgt].append({
                        "target_title": src,
                        "relation_type": "backlink",
                        "edge_weight": round(float(row["edge_weight"]) * 0.7, 4),
                    })
            return adj

    # =========================================================================
    # Epistemic Conflicts & Truth Maintenance (ATMS)
    # =========================================================================

    def log_conflict(self, old_note_id: Any, new_note_id: Any, conflict_description: str) -> int:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO epistemic_conflicts (old_note_id, new_note_id, conflict_description, resolution_status, detected_at)
                VALUES (?, ?, ?, 'pending', datetime('now'));
            """,
                (str(old_note_id), str(new_note_id), conflict_description),
            )
            return cur.lastrowid

    def get_pending_conflicts(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT ec.id, ec.old_note_id, no.title AS old_title,
                       ec.new_note_id, nn.title AS new_title,
                       ec.conflict_description, ec.resolution_status, ec.detected_at
                FROM epistemic_conflicts ec
                LEFT JOIN notes no ON no.id = ec.old_note_id
                LEFT JOIN notes nn ON nn.id = ec.new_note_id
                WHERE ec.resolution_status = 'pending'
                ORDER BY ec.id DESC
                LIMIT ?;
            """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def resolve_conflict_supersede(self, old_id: Any, new_id: Any, resolved_by: str = "system") -> bool:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE notes
                SET superseded_by = ?, status = 'deprecated', updated_at = datetime('now')
                WHERE id = ?;
            """,
                (str(new_id), str(old_id)),
            )
            cur.execute(
                """
                INSERT OR IGNORE INTO links (id, source_note_id, target_note_id, link_type, relation_type, edge_weight)
                VALUES (?, ?, ?, 'wiki', 'supersedes', 2.0);
            """,
                (str(uuid.uuid4()), str(new_id), str(old_id)),
            )
            cur.execute(
                """
                UPDATE epistemic_conflicts
                SET resolution_status = 'superseded', resolved_by = ?
                WHERE old_note_id = ? AND new_note_id = ?;
            """,
                (resolved_by, str(old_id), str(new_id)),
            )
            return True
