import hashlib
import json
import logging
import math
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    from psycopg2.pool import ThreadedConnectionPool
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    ThreadedConnectionPool = None
    Json = None

from .base import MemoryStore

logger = logging.getLogger("gomaa-postgres")


class PgVectorStore(MemoryStore):
    def __init__(self, dsn: str, minconn: int = 1, maxconn: int = 10):
        if psycopg2 is None:
            raise ImportError("psycopg2 is required for PostgreSQL store. Install with: pip install 'gomaa[postgres]'")
        self.dsn = dsn
        self._minconn = minconn
        self._maxconn = maxconn
        self._pool = ThreadedConnectionPool(self._minconn, self._maxconn, dsn=self.dsn)
        self._ensure_schema()

    @contextmanager
    def _conn(self):
        """Thread-safe connection pool manager with stale connection eviction."""
        conn = self._pool.getconn()
        try:
            if conn.closed != 0:
                self._pool.putconn(conn, close=True)
                conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception:
            try:
                if not conn.closed:
                    conn.rollback()
            except Exception:
                pass
            raise
        finally:
            if conn.closed:
                try:
                    self._pool.putconn(conn, close=True)
                except Exception:
                    pass
            else:
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
                        memory_type VARCHAR(32) NOT NULL DEFAULT 'semantic',
                        episodic_parent_hash VARCHAR(64),
                        superseded_by INT REFERENCES notes(id),
                        access_count INT DEFAULT 0,
                        confidence REAL DEFAULT 1.0,
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
                        relation_type VARCHAR(64) NOT NULL DEFAULT 'associative',
                        edge_weight REAL DEFAULT 1.0,
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

                    CREATE TABLE IF NOT EXISTS episodic_events (
                        id BIGSERIAL PRIMARY KEY,
                        event_uuid VARCHAR(64) UNIQUE,
                        session_id VARCHAR(64) NOT NULL,
                        turn_index INT NOT NULL,
                        origin_agent VARCHAR(64) NOT NULL,
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        event_type VARCHAR(32) NOT NULL,
                        stimulus TEXT NOT NULL,
                        response TEXT NOT NULL,
                        outcome_status VARCHAR(16) DEFAULT 'success',
                        surprise_factor REAL DEFAULT 0.0,
                        content_hash VARCHAR(64) NOT NULL,
                        consolidated BOOLEAN DEFAULT FALSE,
                        embedding vector(384)
                    );
                    CREATE INDEX IF NOT EXISTS idx_episodic_unconsolidated ON episodic_events (consolidated, timestamp);
                    CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_events (session_id, turn_index);

                    CREATE TABLE IF NOT EXISTS procedural_playbooks (
                        id SERIAL PRIMARY KEY,
                        skill_name VARCHAR(128) NOT NULL UNIQUE,
                        domain VARCHAR(64) NOT NULL,
                        description TEXT NOT NULL,
                        preconditions JSONB NOT NULL DEFAULT '[]',
                        tool_sequence JSONB NOT NULL DEFAULT '[]',
                        error_recovery JSONB NOT NULL DEFAULT '{}',
                        invocation_count INT DEFAULT 0,
                        success_count INT DEFAULT 0,
                        embedding vector(384),
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_procedural_domain ON procedural_playbooks (domain);

                    CREATE TABLE IF NOT EXISTS working_memory (
                        session_id VARCHAR(64) PRIMARY KEY,
                        agent_role VARCHAR(64) NOT NULL,
                        active_goal TEXT,
                        subtask_stack JSONB DEFAULT '[]',
                        hypotheses JSONB DEFAULT '[]',
                        attention_window JSONB DEFAULT '[]',
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS epistemic_conflicts (
                        id SERIAL PRIMARY KEY,
                        old_note_id INT REFERENCES notes(id) ON DELETE CASCADE,
                        new_note_id INT REFERENCES notes(id) ON DELETE CASCADE,
                        detected_at TIMESTAMPTZ DEFAULT NOW(),
                        conflict_description TEXT NOT NULL,
                        resolution_status VARCHAR(32) DEFAULT 'pending',
                        resolved_by VARCHAR(64)
                    );
                """
                )
                cur.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'notes';
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
                if "memory_type" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN memory_type VARCHAR(32) NOT NULL DEFAULT 'semantic';")
                if "episodic_parent_hash" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN episodic_parent_hash VARCHAR(64);")
                if "superseded_by" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN superseded_by INT REFERENCES notes(id);")
                if "access_count" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN access_count INT DEFAULT 0;")
                if "confidence" not in existing:
                    cur.execute("ALTER TABLE notes ADD COLUMN confidence REAL DEFAULT 1.0;")

                cur.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'links';
                """
                )
                link_cols = {row[0] for row in cur.fetchall()}
                if "relation_type" not in link_cols:
                    cur.execute("ALTER TABLE links ADD COLUMN relation_type VARCHAR(64) NOT NULL DEFAULT 'associative';")
                if "edge_weight" not in link_cols:
                    cur.execute("ALTER TABLE links ADD COLUMN edge_weight REAL DEFAULT 1.0;")

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

    def log_timeline(
        self, action: str, note_title: Optional[str] = None, query: Optional[str] = None, summary: Optional[str] = None
    ) -> None:
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
        memory_type: str = "semantic",
        episodic_parent_hash: Optional[str] = None,
        superseded_by: Optional[int] = None,
        confidence: float = 1.0,
    ) -> int:
        vault_path = str(vault_path)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title, content, tags, salience, access_count FROM notes WHERE title = %s AND vault_path = %s;",
                    (title, vault_path),
                )
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
                    INSERT INTO notes (
                        title, content, tags, note_type, status, salience, embedding,
                        vault_path, wing, room, origin_agent, memory_type,
                        episodic_parent_hash, superseded_by, confidence, access_count,
                        last_accessed_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, NOW(), NOW())
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
                        memory_type = EXCLUDED.memory_type,
                        episodic_parent_hash = EXCLUDED.episodic_parent_hash,
                        superseded_by = EXCLUDED.superseded_by,
                        confidence = EXCLUDED.confidence,
                        access_count = notes.access_count + 1,
                        last_accessed_at = NOW(),
                        updated_at = NOW()
                    RETURNING id;
                """,
                    (
                        title,
                        content,
                        tags,
                        note_type,
                        status,
                        salience,
                        embedding,
                        vault_path,
                        wing,
                        room,
                        origin_agent,
                        memory_type,
                        episodic_parent_hash,
                        superseded_by,
                        confidence,
                    ),
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
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
        scope: Optional[Dict] = None,
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
                           1 - (embedding <=> %s::vector) AS score,
                           memory_type, episodic_parent_hash, superseded_by, access_count, confidence
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
                            "memory_type": row[10] or "semantic",
                            "episodic_parent_hash": row[11],
                            "superseded_by": row[12],
                            "access_count": row[13] or 0,
                            "confidence": float(row[14]) if row[14] is not None else 1.0,
                        }
                    )
                # Selective access touch (only high-confidence matches >= 0.55)
                high_conf_ids = [r["id"] for r in results if r["score"] >= 0.55]
                if high_conf_ids:
                    cur.execute(
                        "UPDATE notes SET last_accessed_at = NOW(), access_count = COALESCE(access_count, 0) + 1 WHERE id = ANY(%s);",
                        (high_conf_ids,),
                    )
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
                           ts_rank_cd(tsv, websearch_to_tsquery('english', %s), 32) AS score,
                           memory_type, episodic_parent_hash, superseded_by, access_count, confidence
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
                            "memory_type": row[10] or "semantic",
                            "episodic_parent_hash": row[11],
                            "superseded_by": row[12],
                            "access_count": row[13] or 0,
                            "confidence": float(row[14]) if row[14] is not None else 1.0,
                        }
                    )
                # Selective access touch (score >= 0.02)
                high_conf_ids = [r["id"] for r in results if r["score"] >= 0.02]
                if high_conf_ids:
                    cur.execute(
                        "UPDATE notes SET last_accessed_at = NOW(), access_count = COALESCE(access_count, 0) + 1 WHERE id = ANY(%s);",
                        (high_conf_ids,),
                    )
                return results

    def search_graph(self, note_title: str, depth: int = 2, top_k: int = 10) -> List[Dict]:
        """Graph search with formal cycle detection (immune to infinite loops on circular links)."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH RECURSIVE graph_walk AS (
                        SELECT (CASE WHEN l.source_note_id = n.id THEN l.target_note_id ELSE l.source_note_id END) AS note_id, 1 AS depth, ARRAY[l.source_note_id, l.target_note_id] AS path
                        FROM links l
                        JOIN notes n ON (n.id = l.source_note_id OR n.id = l.target_note_id)
                        WHERE (n.title = %s OR n.title ILIKE %s) AND n.status = 'active'
                        UNION
                        SELECT (CASE WHEN l.source_note_id = gw.note_id THEN l.target_note_id ELSE l.source_note_id END), gw.depth + 1, gw.path || (CASE WHEN l.source_note_id = gw.note_id THEN l.target_note_id ELSE l.source_note_id END)
                        FROM links l
                        JOIN graph_walk gw ON (gw.note_id = l.source_note_id OR gw.note_id = l.target_note_id)
                        WHERE gw.depth < %s AND NOT ((CASE WHEN l.source_note_id = gw.note_id THEN l.target_note_id ELSE l.source_note_id END) = ANY(gw.path))
                    )
                    SELECT DISTINCT ON (n.id) n.id, n.title, n.content, n.tags, n.salience, n.vault_path, n.wing, n.room, gw.depth
                    FROM graph_walk gw
                    JOIN notes n ON n.id = gw.note_id
                    WHERE n.status = 'active'
                    ORDER BY n.id, gw.depth ASC
                    LIMIT %s;
                """,
                    (note_title, f"%{note_title}%", depth, top_k),
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

    def search_associative_ppr(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        scope: Optional[Dict] = None,
        restart_prob: float = 0.15,
    ) -> List[Dict[str, Any]]:
        """
        HippoRAG 2 Personalized PageRank associative search.
        Seeds nodes from dense vector similarity, diffusing activation across graph topology.
        """
        seeds = self.search_semantic(query_embedding, top_k=5, scope=scope)
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

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, content, tags, note_type, salience, vault_path, wing, room, access_count, confidence
                    FROM notes
                    WHERE title = ANY(%s) AND status = 'active';
                """,
                    (titles,),
                )
                note_dict = {}
                for row in cur.fetchall():
                    note_dict[row[1]] = {
                        "id": row[0],
                        "title": row[1],
                        "content": row[2],
                        "tags": row[3] or [],
                        "note_type": row[4],
                        "salience": row[5],
                        "vault_path": row[6],
                        "wing": row[7],
                        "room": row[8],
                        "access_count": row[9] or 0,
                        "confidence": row[10] or 1.0,
                        "ppr_score": score_map.get(row[1], 0.0),
                        "score": score_map.get(row[1], 0.0),
                    }

                results = [note_dict[t] for t in titles if t in note_dict]
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
        ppr_results = self.search_associative_ppr(query_embedding, top_k=top_k * 2, scope=scope)

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
        add_results(ppr_results, "hipporag_ppr", 1.2)

        for nid in scores:
            salience = scores[nid].get("salience", 0.5)
            access_count = scores[nid].get("access_count", 0)
            confidence = scores[nid].get("confidence", 1.0)
            # ACT-R dynamic activation bonus
            actr_bonus = 0.005 * salience + 0.002 * math.log(1 + max(0, access_count)) * confidence
            scores[nid]["rrf_score"] += actr_bonus

        sorted_results = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        return sorted_results[:top_k]

    def apply_decay(self, decay_rate: float = 0.95, archive_threshold: float = 0.05) -> Dict:
        """Apply Ebbinghaus decay with pinned / permanent immunity."""
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notes
                    SET salience = salience * %s::float
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

    def schedule_reminder(self, title: str, content: str, trigger_at: str, recurring: Optional[str] = None) -> str:
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

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO episodic_events (
                        event_uuid, session_id, turn_index, origin_agent,
                        event_type, stimulus, response, outcome_status,
                        surprise_factor, content_hash, consolidated, embedding, timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, NOW())
                    RETURNING id;
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
                        embedding,
                    ),
                )
                event_id = cur.fetchone()[0]
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
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, event_uuid, session_id, turn_index, origin_agent,
                           timestamp, event_type, stimulus, response, outcome_status,
                           surprise_factor, content_hash, consolidated, embedding
                    FROM episodic_events
                    WHERE consolidated = FALSE
                    ORDER BY timestamp ASC
                    LIMIT %s;
                """,
                    (limit,),
                )
                results = []
                for row in cur.fetchall():
                    d = dict(row)
                    d["consolidated"] = bool(d["consolidated"])
                    results.append(d)
                return results

    def mark_events_consolidated(self, event_ids: List[Any]) -> int:
        if not event_ids:
            return 0
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE episodic_events SET consolidated = TRUE WHERE id = ANY(%s);",
                    (event_ids,),
                )
                return cur.rowcount

    def get_episodic_events(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if session_id:
                    cur.execute(
                        """
                        SELECT id, event_uuid, session_id, turn_index, origin_agent,
                               timestamp, event_type, stimulus, response, outcome_status,
                               surprise_factor, content_hash, consolidated, embedding
                        FROM episodic_events
                        WHERE session_id = %s
                        ORDER BY turn_index ASC, timestamp ASC
                        LIMIT %s;
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
                        LIMIT %s;
                    """,
                        (limit,),
                    )
                results = []
                for row in cur.fetchall():
                    d = dict(row)
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
        precond_json = Json(preconditions) if Json else json.dumps(preconditions)
        tool_seq_json = Json(tool_sequence) if Json else json.dumps(tool_sequence)
        recovery_json = Json(error_recovery) if Json else json.dumps(error_recovery)

        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO procedural_playbooks (
                        skill_name, domain, description, preconditions, tool_sequence,
                        error_recovery, invocation_count, success_count, embedding, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 0, 0, %s, NOW(), NOW())
                    ON CONFLICT (skill_name) DO UPDATE SET
                        domain = EXCLUDED.domain,
                        description = EXCLUDED.description,
                        preconditions = EXCLUDED.preconditions,
                        tool_sequence = EXCLUDED.tool_sequence,
                        error_recovery = EXCLUDED.error_recovery,
                        embedding = COALESCE(EXCLUDED.embedding, procedural_playbooks.embedding),
                        updated_at = NOW()
                    RETURNING id, invocation_count, success_count;
                """,
                    (skill_name, domain, description, precond_json, tool_seq_json, recovery_json, embedding),
                )
                row = cur.fetchone()
                pid, inv, succ = row[0], row[1], row[2]
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
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_clauses = []
                params: List[Any] = []
                if domain:
                    where_clauses.append("domain = %s")
                    params.append(domain)

                where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

                if query_embedding:
                    params_all = [query_embedding] + params + [query_embedding, limit]
                    sql = f"""
                        SELECT id, skill_name, domain, description, preconditions, tool_sequence,
                               error_recovery, invocation_count, success_count,
                               COALESCE(1 - (embedding <=> %s::vector), (success_count + 1.0) / (invocation_count + 2.0)) AS score
                        FROM procedural_playbooks
                        {where_sql}
                        ORDER BY embedding <=> %s::vector ASC NULLS LAST
                        LIMIT %s;
                    """
                    cur.execute(sql, params_all)
                else:
                    params.append(limit)
                    sql = f"""
                        SELECT id, skill_name, domain, description, preconditions, tool_sequence,
                               error_recovery, invocation_count, success_count,
                               (success_count + 1.0) / (invocation_count + 2.0) AS score
                        FROM procedural_playbooks
                        {where_sql}
                        ORDER BY (success_count + 1.0) / (invocation_count + 2.0) DESC
                        LIMIT %s;
                    """
                    cur.execute(sql, params)

                rows = cur.fetchall()
                results = []
                for row in rows:
                    p = dict(row)
                    p["bayesian_success_rate"] = (p["success_count"] + 1.0) / (p["invocation_count"] + 2.0)
                    if p.get("score") is None:
                        p["score"] = p["bayesian_success_rate"]
                    results.append(p)
                return results

    def record_playbook_execution(self, skill_name: str, success: bool) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                succ_inc = 1 if success else 0
                cur.execute(
                    """
                    UPDATE procedural_playbooks
                    SET invocation_count = invocation_count + 1,
                        success_count = success_count + %s,
                        updated_at = NOW()
                    WHERE skill_name = %s;
                """,
                    (succ_inc, skill_name),
                )
                return cur.rowcount > 0

    def get_playbook(self, skill_name: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, skill_name, domain, description, preconditions, tool_sequence,
                           error_recovery, invocation_count, success_count
                    FROM procedural_playbooks
                    WHERE skill_name = %s;
                """,
                    (skill_name,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                p = dict(row)
                p["bayesian_success_rate"] = (p["success_count"] + 1.0) / (p["invocation_count"] + 2.0)
                return p

    # =========================================================================
    # Quadrant 3: Working Memory Buffer
    # =========================================================================

    def get_working_memory(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT session_id, agent_role, active_goal, subtask_stack, hypotheses, attention_window, updated_at
                    FROM working_memory
                    WHERE session_id = %s;
                """,
                    (session_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

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
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT active_goal, subtask_stack, hypotheses, attention_window FROM working_memory WHERE session_id = %s;",
                    (session_id,),
                )
                existing = cur.fetchone()

                goal_val = active_goal if active_goal is not None else (existing[0] if existing else None)
                subtask_val = Json(subtask_stack) if subtask_stack is not None else (existing[1] if existing else Json([]))
                hypo_val = Json(hypotheses) if hypotheses is not None else (existing[2] if existing else Json([]))
                attn_val = Json(attention_window) if attention_window is not None else (existing[3] if existing else Json([]))

                cur.execute(
                    """
                    INSERT INTO working_memory (session_id, agent_role, active_goal, subtask_stack, hypotheses, attention_window, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (session_id) DO UPDATE SET
                        agent_role = EXCLUDED.agent_role,
                        active_goal = EXCLUDED.active_goal,
                        subtask_stack = EXCLUDED.subtask_stack,
                        hypotheses = EXCLUDED.hypotheses,
                        attention_window = EXCLUDED.attention_window,
                        updated_at = NOW();
                """,
                    (session_id, agent_role, goal_val, subtask_val, hypo_val, attn_val),
                )
                return {
                    "session_id": session_id,
                    "agent_role": agent_role,
                    "active_goal": goal_val,
                    "subtask_stack": subtask_stack if subtask_stack is not None else (existing[1] if existing else []),
                    "hypotheses": hypotheses if hypotheses is not None else (existing[2] if existing else []),
                    "attention_window": attention_window if attention_window is not None else (existing[3] if existing else []),
                }

    def clear_working_memory(self, session_id: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM working_memory WHERE session_id = %s;", (session_id,))
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
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO links (source_note_id, target_note_id, link_type, relation_type, edge_weight, created_at)
                    VALUES (%s, %s, 'wiki', %s, %s, NOW())
                    ON CONFLICT (source_note_id, target_note_id) DO UPDATE SET
                        relation_type = EXCLUDED.relation_type,
                        edge_weight = EXCLUDED.edge_weight;
                """,
                    (int(source_id), int(target_id), relation_type, float(weight)),
                )
                return True

    def get_graph_adjacency(self) -> Dict[str, List[Dict[str, Any]]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO epistemic_conflicts (old_note_id, new_note_id, conflict_description, resolution_status, detected_at)
                    VALUES (%s, %s, %s, 'pending', NOW())
                    RETURNING id;
                """,
                    (int(old_note_id), int(new_note_id), conflict_description),
                )
                return cur.fetchone()[0]

    def get_pending_conflicts(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
                    LIMIT %s;
                """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]

    def resolve_conflict_supersede(self, old_id: Any, new_id: Any, resolved_by: str = "system") -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notes
                    SET superseded_by = %s, status = 'deprecated', updated_at = NOW()
                    WHERE id = %s;
                """,
                    (int(new_id), int(old_id)),
                )
                cur.execute(
                    """
                    INSERT INTO links (source_note_id, target_note_id, link_type, relation_type, edge_weight)
                    VALUES (%s, %s, 'wiki', 'supersedes', 2.0)
                    ON CONFLICT (source_note_id, target_note_id) DO UPDATE SET
                        relation_type = 'supersedes', edge_weight = 2.0;
                """,
                    (int(new_id), int(old_id)),
                )
                cur.execute(
                    """
                    UPDATE epistemic_conflicts
                    SET resolution_status = 'superseded', resolved_by = %s
                    WHERE old_note_id = %s AND new_note_id = %s;
                """,
                    (resolved_by, int(old_id), int(new_id)),
                )
                return True
