"""PostgreSQL + pgvector store — Mnemosyne v3.0."""

import os
import logging
import threading
from typing import List, Dict, Optional
from datetime import datetime, timezone

from mnemosyne.stores.base import MemoryStore

logger = logging.getLogger("unified-memory")

DB_DSN = os.environ.get("MEMORY_DB_DSN", "postgresql://localhost:5432/mnemosyne")


class PgVectorStore(MemoryStore):
    """
    PostgreSQL-backed store with pgvector for semantic search,
    tsvector for keyword search, recursive CTEs for graph traversal,
    hierarchical scoping (wing/room), timeline logging, and versioning.
    """

    def __init__(self, dsn: str = DB_DSN):
        self.dsn = dsn
        self._local = threading.local()
        self._init_schema()

    def _conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None or self._local.conn.closed:
            import psycopg2
            self._local.conn = psycopg2.connect(self.dsn)
        return self._local.conn

    def _init_schema(self):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL DEFAULT ,
                        tags TEXT[] DEFAULT {},
                        note_type TEXT DEFAULT concept,
                        status TEXT DEFAULT active,
                        salience FLOAT DEFAULT 0.5,
                        embedding vector(384),
                        vault_path TEXT DEFAULT ,
                        wing TEXT DEFAULT general,
                        room TEXT DEFAULT general,
                        last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
                        tsv tsvector GENERATED ALWAYS AS (
                            setweight(to_tsvector(english, COALESCE(title, )), A) ||
                            setweight(to_tsvector(english, COALESCE(content, )), B)
                        ) STORED,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(title, vault_path)
                    );
                """)
                cur.execute("""CREATE TABLE IF NOT EXISTS links (
                    id SERIAL PRIMARY KEY,
                    source_note_id INTEGER REFERENCES notes(id) ON DELETE CASCADE,
                    target_note_id INTEGER REFERENCES notes(id) ON DELETE CASCADE,
                    link_type TEXT DEFAULT wiki,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(source_note_id, target_note_id)
                );""")
                cur.execute("""CREATE TABLE IF NOT EXISTS prospective (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT DEFAULT ,
                    trigger_at TIMESTAMPTZ NOT NULL,
                    recurring TEXT,
                    status TEXT DEFAULT pending,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );""")
                cur.execute("""CREATE TABLE IF NOT EXISTS timeline (
                    id SERIAL PRIMARY KEY,
                    action TEXT NOT NULL,
                    note_title TEXT,
                    query TEXT,
                    summary TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );""")
                cur.execute("""CREATE TABLE IF NOT EXISTS note_versions (
                    id SERIAL PRIMARY KEY,
                    note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL,
                    title TEXT,
                    content TEXT,
                    tags TEXT[],
                    salience FLOAT,
                    version_at TIMESTAMPTZ DEFAULT NOW()
                );""")
                conn.commit()
                logger.info("Database schema initialized (v3.0).")

    # ─── TIMELINE ───────────────────────────────────────────────

    def log_timeline(self, action: str, note_title: str = None, query: str = None, summary: str = None):
        """Log an operation to the timeline."""
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO timeline (action, note_title, query, summary) VALUES (%s, %s, %s, %s);",
                        (action, note_title, query, summary),
                    )
                    conn.commit()
        except Exception as e:
            logger.warning(f"Timeline log failed: {e}")

    def get_timeline(self, limit: int = 20) -> List[Dict]:
        """Get recent timeline entries."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, action, note_title, query, summary, created_at FROM timeline ORDER BY created_at DESC LIMIT %s;",
                    (limit,),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ─── VERSIONING ─────────────────────────────────────────────

    def _archive_version(self, cur, title: str, vault_path: str):
        """Archive current version before overwriting."""
        cur.execute(
            "SELECT id, content, tags, salience FROM notes WHERE title = %s AND vault_path = %s;",
            (title, vault_path),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                "INSERT INTO note_versions (note_id, title, content, tags, salience) VALUES (%s, %s, %s, %s, %s);",
                (row[0], title, row[1], row[2], row[3]),
            )

    def get_note_history(self, title: str, limit: int = 10) -> List[Dict]:
        """Get version history for a note."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT nv.id, nv.title, LEFT(nv.content, 200) as preview, nv.tags, nv.salience, nv.version_at
                       FROM note_versions nv
                       JOIN notes n ON nv.note_id = n.id
                       WHERE n.title = %s
                       ORDER BY nv.version_at DESC LIMIT %s;""",
                    (title, limit),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ─── UPSERT (with versioning) ──────────────────────────────

    def upsert_note(
        self, title: str, content: str, tags: List[str], note_type: str,
        status: str, salience: float, embedding: List[float], vault_path: str,
        wing: str = "general", room: str = "general",
    ) -> str:
        """Insert or update a note. Archives old version before overwriting."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                self._archive_version(cur, title, vault_path)
                cur.execute(
                    """
                    INSERT INTO notes (
                        title, content, tags, note_type,
                        status, salience, embedding, vault_path,
                        wing, room, last_accessed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (title, vault_path) DO UPDATE SET
                        content = EXCLUDED.content,
                        tags = EXCLUDED.tags,
                        note_type = EXCLUDED.note_type,
                        status = EXCLUDED.status,
                        salience = EXCLUDED.salience,
                        embedding = EXCLUDED.embedding,
                        wing = EXCLUDED.wing,
                        room = EXCLUDED.room,
                        last_accessed_at = NOW(),
                        updated_at = NOW()
                    RETURNING id;
                """,
                    (title, content, tags, note_type, status, salience, embedding, vault_path, wing, room),
                )
                note_id = cur.fetchone()[0]
                conn.commit()
                return note_id

    def delete_note(self, title: str, vault_path: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM notes WHERE title = %s AND vault_path = %s RETURNING id;", (title, vault_path))
                deleted = cur.fetchone()
                conn.commit()
                return deleted is not None

    # ─── SEARCH (with scoping) ─────────────────────────────────

    def _scope_clause(self, scope: Optional[Dict]) -> tuple:
        """Build WHERE clause fragments for wing/room scoping."""
        clauses = []
        params = []
        if scope:
            if scope.get("wing"):
                clauses.append("wing = %s")
                params.append(scope["wing"])
            if scope.get("room"):
                clauses.append("room = %s")
                params.append(scope["room"])
        return " AND ".join(clauses), params

    def search_semantic(
        self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None, scope: Optional[Dict] = None,
    ) -> List[Dict]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                where = "WHERE status = active"
                params = []

                scope_clause, scope_params = self._scope_clause(scope)
                if scope_clause:
                    where += " AND " + scope_clause
                    params.extend(scope_params)

                if filters:
                    if filters.get("tags"):
                        where += " AND tags && %s"
                        params.append(filters["tags"])
                    if filters.get("note_type"):
                        where += " AND note_type = %s"
                        params.append(filters["note_type"])

                params.extend([query_embedding, query_embedding, top_k])

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
                # Touch last_accessed_at for returned results
                cols = [d[0] for d in cur.description]
                results = [dict(zip(cols, row)) for row in cur.fetchall()]
                if results:
                    ids = [r["id"] for r in results]
                    cur.execute("UPDATE notes SET last_accessed_at = NOW() WHERE id = ANY(%s);", (ids,))
                    conn.commit()
                return results

    def search_keyword(self, query: str, top_k: int = 10, scope: Optional[Dict] = None) -> List[Dict]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                where = "WHERE status = active AND tsv @@ plainto_tsquery(english, %s)"
                params = [query]

                scope_clause, scope_params = self._scope_clause(scope)
                if scope_clause:
                    where += " AND " + scope_clause
                    params.extend(scope_params)

                params.extend([query, top_k])

                cur.execute(
                    f"""
                    SELECT id, title, content, tags, note_type, salience, vault_path, wing, room,
                           ts_rank_cd(tsv, plainto_tsquery(english, %s), 32) AS score
                    FROM notes
                    {where}
                    ORDER BY score DESC
                    LIMIT %s;
                """,
                    params,
                )
                cols = [d[0] for d in cur.description]
                results = [dict(zip(cols, row)) for row in cur.fetchall()]
                if results:
                    ids = [r["id"] for r in results]
                    cur.execute("UPDATE notes SET last_accessed_at = NOW() WHERE id = ANY(%s);", (ids,))
                    conn.commit()
                return results

    def search_graph(self, note_title: str, depth: int = 2, top_k: int = 10) -> List[Dict]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH RECURSIVE graph AS (
                        SELECT n.id, n.title, n.content, n.tags, n.salience, n.vault_path, n.wing, n.room,
                               0 AS depth, n.id AS root_id
                        FROM notes n WHERE n.title = %s AND n.status = active
                        UNION ALL
                        SELECT n2.id, n2.title, n2.content, n2.tags, n2.salience, n2.vault_path, n2.wing, n2.room,
                               g.depth + 1, g.root_id
                        FROM graph g
                        JOIN links l ON l.source_note_id = g.id
                        JOIN notes n2 ON n2.id = l.target_note_id
                        WHERE n2.status = active AND g.depth < %s
                    )
                    SELECT DISTINCT id, title, content, tags, salience, vault_path, wing, room, depth
                    FROM graph WHERE depth > 0
                    ORDER BY depth, salience DESC LIMIT %s;
                """,
                    (note_title, depth, top_k),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def hybrid_search(
        self, query: str, query_embedding: List[float], top_k: int = 10, scope: Optional[Dict] = None,
    ) -> List[Dict]:
        """Reciprocal Rank Fusion (RRF) of semantic + keyword + salience."""
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

    # ─── TEMPORAL DECAY ────────────────────────────────────────

    def apply_decay(self, decay_rate: float = 0.95, archive_threshold: float = 0.05) -> Dict:
        """Apply temporal decay. Called during nightly consolidation."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE notes
                    SET salience = salience * POWER(%s, EXTRACT(EPOCH FROM (NOW() - last_accessed_at)) / 86400.0)
                    WHERE status = active AND last_accessed_at < NOW() - INTERVAL 1 day;
                """, (decay_rate,))
                decayed = cur.rowcount

                cur.execute("""
                    UPDATE notes SET status = archived
                    WHERE status = active AND salience < %s;
                """, (archive_threshold,))
                archived = cur.rowcount
                conn.commit()
                return {"decayed": decayed, "archived": archived}

    # ─── LINKS & STATS ─────────────────────────────────────────

    def update_links(self, note_id: str, wiki_links: List[str]):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM links WHERE source_note_id = %s;", (note_id,))
                for target_title in wiki_links:
                    cur.execute(
                        """INSERT INTO links (source_note_id, target_note_id, link_type)
                           SELECT %s, id, wiki FROM notes
                           WHERE title = %s AND status = active
                           ON CONFLICT (source_note_id, target_note_id) DO NOTHING;""",
                        (note_id, target_title.strip()),
                    )
                conn.commit()

    def get_stats(self) -> Dict:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM notes WHERE status = active;")
                note_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM links;")
                link_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM prospective WHERE status = pending;")
                pending = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM timeline;")
                timeline_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM note_versions;")
                version_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM notes WHERE status = archived;")
                archived = cur.fetchone()[0]
                cur.execute("SELECT DISTINCT wing FROM notes WHERE status = active;")
                wings = [r[0] for r in cur.fetchall()]
                return {
                    "notes": note_count,
                    "links": link_count,
                    "pending_reminders": pending,
                    "timeline_entries": timeline_count,
                    "versions": version_count,
                    "archived": archived,
                    "wings": wings,
                    "version": "3.0",
                }
