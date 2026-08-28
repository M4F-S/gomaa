import json
import logging
import re
import sys
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from .base import MemoryStore

logger = logging.getLogger("gomaa-postgres")


class PgVectorStore(MemoryStore):
    def __init__(self, dsn: str, minconn: int = 1, maxconn: int = 10):
        self.dsn = dsn
        self._minconn = minconn
        self._maxconn = maxconn
        self._pool = ThreadedConnectionPool(self._minconn, self._maxconn, dsn=self.dsn)
        self._ensure_schema()

    @contextmanager
    def _conn(self):
        """Thread-safe, self-healing connection pool manager."""
        conn = self._pool.getconn()
        try:
            if conn.closed != 0:
                raise psycopg2.OperationalError("Stale closed connection acquired from pool")
            yield conn
            conn.commit()
        except psycopg2.OperationalError as e:
            logger.warning(f"Evicting dead connection from pool: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            self._pool.putconn(conn, close=True)
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            if not conn.closed:
                self._pool.putconn(conn)

    def close(self):
        if self._pool is not None:
            self._pool.closeall()

    def _ensure_schema(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE EXTENSION IF NOT EXISTS vector;

                    CREATE TABLE IF NOT EXISTS notes (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tags TEXT[] DEFAULT '{}',
                        note_type TEXT NOT NULL DEFAULT 'concept',
                        status TEXT NOT NULL DEFAULT 'active',
                        salience REAL DEFAULT 0.5,
                        embedding vector(384),
                        vault_path TEXT NOT NULL,
                        wing TEXT NOT NULL DEFAULT 'general',
                        room TEXT NOT NULL DEFAULT 'general',
                        origin_agent VARCHAR(64) DEFAULT 'local',
                        last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        tsv tsvector GENERATED ALWAYS AS (
                            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                            setweight(to_tsvector('english', coalesce(content, '')), 'B')
                        ) STORED,
                        CONSTRAINT notes_title_vault_unique UNIQUE (title, vault_path)
                    );

                    -- High-recall HNSW vector index (pgvector >= 0.5.0) with fallback
                    DO $$
                    BEGIN
                        BEGIN
                            CREATE INDEX IF NOT EXISTS notes_embedding_hnsw_idx ON notes USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
                        EXCEPTION WHEN OTHERS THEN
                            CREATE INDEX IF NOT EXISTS notes_embedding_idx ON notes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                        END;
                    END $$;

                    CREATE INDEX IF NOT EXISTS notes_tsv_idx ON notes USING gin (tsv);
                    CREATE INDEX IF NOT EXISTS notes_tags_idx ON notes USING gin (tags);
                    CREATE INDEX IF NOT EXISTS notes_wing_room_idx ON notes (wing, room);
                    CREATE INDEX IF NOT EXISTS notes_status_idx ON notes (status);

                    CREATE TABLE IF NOT EXISTS links (
                        id SERIAL PRIMARY KEY,
                        source_note_id INT REFERENCES notes(id) ON DELETE CASCADE,
                        target_note_id INT REFERENCES notes(id) ON DELETE CASCADE,
                        link_type TEXT NOT NULL DEFAULT 'wiki',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        CONSTRAINT links_unique_edge UNIQUE (source_note_id, target_note_id)
                    );

                    CREATE TABLE IF NOT EXISTS prospective (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT DEFAULT '',
                        trigger_at TIMESTAMPTZ NOT NULL,
                        recurring TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS timeline (
                        id SERIAL PRIMARY KEY,
                        action TEXT NOT NULL,
                        note_title TEXT,
                        query TEXT,
                        summary TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS note_versions (
                        id SERIAL PRIMARY KEY,
                        note_id INT REFERENCES notes(id) ON DELETE CASCADE,
                        title TEXT,
                        content TEXT,
                        tags TEXT[],
                        salience REAL,
                        version_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """
                )
                cur.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'notes' AND column_name IN ('wing', 'room', 'last_accessed_at', 'origin_agent');
                """
                )
                existing = {row[0] for row in cur.fetchall()}
                if "wing" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN wing TEXT NOT NULL DEFAULT 'general';")
                if "room" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN room TEXT NOT NULL DEFAULT 'general';")
                if "origin_agent" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN origin_agent VARCHAR(64) DEFAULT 'local';")
                if "last_accessed_at" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")

    def _scope_clause(self, scope: Optional[Dict]) -> Tuple[str, List[Any]]:
        if not scope:
            return "", []
        clauses, params = [], []
        if scope.get("wing"):
            clauses.append("wing = %s")
            params.append(scope["wing"])
        if scope.get("room"):
            clauses.append("room = %s")
            params.append(scope["room"])
        return " AND ".join(clauses), params

    def log_timeline(self, action: str, note_title: Optional[str] = None, query: Optional[str] = None, summary: Optional[str] = None) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO timeline (action, note_title, query, summary)
                    VALUES (%s, %s, %s, %s);
                """,
                    (action, note_title, query, summary),
                )

    def get_timeline(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, action, action AS operation, note_title, note_title AS title, query, summary, created_at
                    FROM timeline
                    ORDER BY id DESC
                    LIMIT %s;
                """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_note_history(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT v.id, v.title, v.content AS preview, v.tags, v.salience, v.version_at
                    FROM note_versions v
                    JOIN notes n ON n.id = v.note_id
                    WHERE n.title = %s
                    ORDER BY v.id DESC
                    LIMIT %s;
                """,
                    (title, limit),
                )
                return [dict(row) for row in cur.fetchall()]

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
    ) -> int:
        vault_path = str(vault_path)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, content, tags, salience FROM notes WHERE title = %s AND vault_path = %s;", (title, vault_path))
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        INSERT INTO note_versions (note_id, title, content, tags, salience)
                        VALUES (%s, %s, %s, %s, %s);
                    """,
                        (existing[0], existing[1], existing[2], existing[3], existing[4]),
                    )

                cur.execute(
                    """
                    INSERT INTO notes (title, content, tags, note_type, status, salience, embedding, vault_path, wing, room, origin_agent, last_accessed_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (title, vault_path) DO UPDATE SET
                        content = EXCLUDED.content,
                        tags = EXCLUDED.tags,
                        note_type = EXCLUDED.note_type,
                        status = EXCLUDED.status,
                        salience = EXCLUDED.salience,
                        embedding = COALESCE(EXCLUDED.embedding, notes.embedding),
                        wing = EXCLUDED.wing,
                        room = EXCLUDED.room,
                        origin_agent = EXCLUDED.origin_agent,
                        last_accessed_at = NOW(),
                        updated_at = NOW()
                    RETURNING id;
                """,
                    (title, content, tags, note_type, status, salience, embedding, vault_path, wing, room, origin_agent),
                )
                note_id = cur.fetchone()[0]

                # Real-Time $O(1)$ Reverse Wikilink Resolution
                cur.execute(
                    """
                    INSERT INTO links (source_note_id, target_note_id, link_type)
                    SELECT n.id, %s, 'wiki'
                    FROM notes n
                    WHERE n.content LIKE %s AND n.status = 'active' AND n.id != %s
                    ON CONFLICT (source_note_id, target_note_id) DO NOTHING;
                """,
                    (note_id, f"%[[{title}%", note_id),
                )

                return note_id

    def delete_note(self, title: str, vault_path: str = "") -> bool:
        vault_path = str(vault_path)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM notes WHERE title = %s AND vault_path = %s;", (title, vault_path))
                return cur.rowcount > 0

    def search_semantic(
        self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None, scope: Optional[Dict] = None,
    ) -> List[Dict]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                where = "WHERE status = 'active'"
                where_params = []

                scope_clause, scope_params = self._scope_clause(scope)
                if scope_clause:
                    where += " AND " + scope_clause
                    where_params.extend(scope_params)

                if filters:
                    if filters.get("tags"):
                        where += " AND tags && %s"
                        where_params.append(filters["tags"])
                    if filters.get("note_type"):
                        where += " AND note_type = %s"
                        where_params.append(filters["note_type"])

                params = [query_embedding] + where_params + [query_embedding, top_k]

                cur.execute(
                    f"""
                    SELECT id, title, content, tags, note_type, salience, vault_path, wing, room,
                           1 - (embedding <=> %s::vector) AS score
                    FROM notes
                    {where}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                """,
                    params,
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    results.append(
                        {
                            "id": row[0],
                            "title": row[1],
                            "content": row[2],
                            "tags": row[3],
                            "note_type": row[4],
                            "salience": row[5],
                            "vault_path": row[6],
                            "wing": row[7],
                            "room": row[8],
                            "score": float(row[9]) if row[9] is not None else 0.0,
                        }
                    )
                # Selective access touch (only high-confidence matches >= 0.55)
                high_conf_ids = [r["id"] for r in results if r["score"] >= 0.55]
                if high_conf_ids:
                    cur.execute("UPDATE notes SET last_accessed_at = NOW() WHERE id = ANY(%s);", (high_conf_ids,))
                return results

    def search_keyword(self, query: str, top_k: int = 10, scope: Optional[Dict] = None) -> List[Dict]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                where = "WHERE status = 'active' AND tsv @@ websearch_to_tsquery('english', %s)"
                where_params = [query]

                scope_clause, scope_params = self._scope_clause(scope)
                if scope_clause:
                    where += " AND " + scope_clause
                    where_params.extend(scope_params)

                params = [query] + where_params + [top_k]

                cur.execute(
                    f"""
                    SELECT id, title, content, tags, note_type, salience, vault_path, wing, room,
                           ts_rank_cd(tsv, websearch_to_tsquery('english', %s), 32) AS score
                    FROM notes
                    {where}
                    ORDER BY score DESC
                    LIMIT %s;
                """,
                    params,
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    results.append(
                        {
                            "id": row[0],
                            "title": row[1],
                            "content": row[2],
                            "tags": row[3],
                            "note_type": row[4],
                            "salience": row[5],
                            "vault_path": row[6],
                            "wing": row[7],
                            "room": row[8],
                            "score": float(row[9]),
                        }
                    )
                # Selective access touch (score >= 0.02)
                high_conf_ids = [r["id"] for r in results if r["score"] >= 0.02]
                if high_conf_ids:
                    cur.execute("UPDATE notes SET last_accessed_at = NOW() WHERE id = ANY(%s);", (high_conf_ids,))
                return results

    def search_graph(self, note_title: str, depth: int = 2, top_k: int = 10) -> List[Dict]:
        """Graph search with formal cycle detection (immune to infinite loops on circular links)."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH RECURSIVE graph_walk AS (
                        SELECT target_note_id AS note_id, 1 AS depth, ARRAY[source_note_id, target_note_id] AS path
                        FROM links l
                        JOIN notes n ON n.id = l.source_note_id
                        WHERE n.title = %s AND n.status = 'active'
                        UNION
                        SELECT l.target_note_id, gw.depth + 1, gw.path || l.target_note_id
                        FROM links l
                        JOIN graph_walk gw ON gw.note_id = l.source_note_id
                        WHERE gw.depth < %s AND NOT (l.target_note_id = ANY(gw.path))
                    )
                    SELECT DISTINCT ON (n.id) n.id, n.title, n.content, n.tags, n.salience, n.vault_path, n.wing, n.room, gw.depth
                    FROM graph_walk gw
                    JOIN notes n ON n.id = gw.note_id
                    WHERE n.status = 'active'
                    ORDER BY n.id, gw.depth ASC
                    LIMIT %s;
                """,
                    (note_title, depth, top_k),
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    results.append(
                        {
                            "id": row[0],
                            "title": row[1],
                            "content": row[2],
                            "tags": row[3],
                            "salience": row[4],
                            "vault_path": row[5],
                            "wing": row[6],
                            "room": row[7],
                            "depth": row[8],
                        }
                    )
                return results

    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        scope: Optional[Dict] = None,
    ) -> List[Dict]:
        semantic = self.search_semantic(query_embedding, top_k=top_k * 2, scope=scope)
        keyword = self.search_keyword(query, top_k=top_k * 2, scope=scope)

        scores: Dict[int, Dict] = {}

        def add_results(results, source, weight):
            for rank, r in enumerate(results, 1):
                nid = r["id"]
                if nid not in scores:
                    scores[nid] = dict(r)
                    scores[nid]["rrf_score"] = 0.0
                    scores[nid]["sources"] = []
                scores[nid]["rrf_score"] += weight * (1.0 / (60 + rank))
                scores[nid]["sources"].append(source)

        add_results(semantic, "semantic", 1.0)
        add_results(keyword, "keyword", 0.8)

        for nid in scores:
            scores[nid]["rrf_score"] += scores[nid].get("salience", 0.5) * 0.005

        sorted_results = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        return sorted_results[:top_k]

    def apply_decay(self, decay_rate: float = 0.95, archive_threshold: float = 0.05) -> Dict:
        """Apply Ebbinghaus decay with pinned / permanent immunity."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notes
                    SET salience = salience * power(%s::float, EXTRACT(EPOCH FROM (NOW() - last_accessed_at)) / 86400.0)
                    WHERE status = 'active'
                      AND last_accessed_at < NOW() - INTERVAL '1 day'
                      AND NOT ('pinned' = ANY(tags) OR 'permanent' = ANY(tags) OR 'core' = ANY(tags))
                      AND salience < 1.0;
                """,
                    (decay_rate,),
                )
                decayed = cur.rowcount

                cur.execute(
                    """
                    UPDATE notes
                    SET status = 'archived'
                    WHERE status = 'active'
                      AND salience < %s
                      AND NOT ('pinned' = ANY(tags) OR 'permanent' = ANY(tags) OR 'core' = ANY(tags))
                      AND salience < 1.0;
                """,
                    (archive_threshold,),
                )
                archived = cur.rowcount

                return {"decayed": decayed, "archived": archived}

    def archive_stale(self, archive_threshold: float = 0.10, days: int = 90) -> int:
        """Archive notes not updated in N days with salience below threshold."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notes
                    SET status = 'archived'
                    WHERE status = 'active'
                      AND updated_at < NOW() - make_interval(days => %s)
                      AND salience < %s
                      AND NOT ('pinned' = ANY(tags) OR 'permanent' = ANY(tags) OR 'core' = ANY(tags))
                      AND salience < 1.0;
                """,
                    (int(days), archive_threshold),
                )
                return cur.rowcount

    def update_links(self, note_id: int, wiki_links: List[str]) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM links WHERE source_note_id = %s;", (note_id,))
                for target_title in wiki_links:
                    cur.execute("SELECT id FROM notes WHERE title = %s AND status = 'active';", (target_title.strip(),))
                    target = cur.fetchone()
                    if target:
                        cur.execute(
                            """
                            INSERT INTO links (source_note_id, target_note_id, link_type)
                            VALUES (%s, %s, 'wiki')
                            ON CONFLICT (source_note_id, target_note_id) DO NOTHING;
                        """,
                            (note_id, target[0]),
                        )

    def reconcile_links(self) -> int:
        """Set-based single-query graph reconciliation."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO links (source_note_id, target_note_id, link_type)
                    SELECT n.id, target.id, 'wiki'
                    FROM notes n
                    CROSS JOIN LATERAL regexp_matches(n.content, '\\[\\[([^\\]|#]+)(?:#[^\\]|]+)?(?:\\|[^\\]]+)?\\]\\]', 'g') AS m(match)
                    JOIN notes target ON target.title = trim(m.match[1]) AND target.status = 'active'
                    WHERE n.status = 'active' AND n.id != target.id
                    ON CONFLICT (source_note_id, target_note_id) DO NOTHING;
                """
                )
                return cur.rowcount

    def get_stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM notes WHERE status = 'active';")
                note_count = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM notes WHERE status = 'archived';")
                archived_count = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM links;")
                link_count = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM prospective WHERE status = 'pending';")
                pending_reminders = cur.fetchone()[0]
                cur.execute("SELECT DISTINCT wing FROM notes WHERE status = 'active';")
                wings = [row[0] for row in cur.fetchall()]
                return {
                    "notes": note_count,
                    "archived": archived_count,
                    "links": link_count,
                    "pending_reminders": pending_reminders,
                    "wings": wings,
                    "backend": "postgresql",
                }

    # --- Prospective-reminder support (store-native, backend-consistent) ---
    # Same interface as SQLiteStore.schedule_reminder / get_due_reminders /
    # mark_reminder_done so ProspectiveMemory can delegate uniformly.

    def schedule_reminder(self, title: str, content: str, trigger_at: str,
                          recurring: Optional[str] = None) -> str:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO prospective (title, content, trigger_at, recurring, status) "
                    "VALUES (%s, %s, %s, %s, 'pending') RETURNING id;",
                    (title, content, trigger_at, recurring),
                )
                rid = cur.fetchone()[0]
        return str(rid)

    def get_due_reminders(self, window_hours: int = 24) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title, content, trigger_at, recurring FROM prospective "
                    "WHERE status = 'pending' AND trigger_at <= NOW() + make_interval(hours => %s) "
                    "ORDER BY trigger_at;",
                    (int(window_hours),),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def mark_reminder_done(self, reminder_id: str) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE prospective SET status = 'done' WHERE id = %s;", (reminder_id,))
