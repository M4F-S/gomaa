# BUILD SESSION: Phase 1 - SQLite Fallback
## Task: Add SQLite store for zero-config installs

**Repository:** `github.com/M4F-S/mo-graphify-obsidian-memory`
**Branch from:** `develop`
**New branch:** `feature/phase-1-sqlite-fallback`

---

## ⚠️ CRITICAL: YOU HAVE ZERO CONTEXT

This is a fresh session. All info is in this prompt. Read carefully before starting.

---

## 1. PROJECT OVERVIEW

**Mnemosyne** is a local-first memory system for AI agents. All code is in the `mnemosyne/` package.

**Current state (Phase 0 complete):**
- `mnemosyne/stores/postgres.py` — `PgVectorStore` works with PostgreSQL + pgvector
- `mnemosyne/core.py` — `UnifiedMemorySystem` directly instantiates `PgVectorStore`
- `mnemosyne/embedder.py` — `Embedder` creates 384-dim vectors
- `mnemosyne/vault.py` — `VaultManager` handles Markdown files

**Your job:** Add SQLite as a fallback so users can try Mnemosyne WITHOUT installing PostgreSQL.

---

## 2. STEP 1: READ CURRENT CODE

Use GitHub MCP to read these files from `develop` branch:

```
owner: M4F-S
repo: mo-graphify-obsidian-memory
branch: develop
files:
  - mnemosyne/stores/__init__.py
  - mnemosyne/stores/postgres.py
  - mnemosyne/core.py
  - mnemosyne/embedder.py
  - mnemosyne/vault.py
```

---

## 3. STEP 2: CREATE BRANCH

```bash
git checkout develop
git pull origin develop
git checkout -b feature/phase-1-sqlite-fallback
```

---

## 4. STEP 3: CREATE ABSTRACT BASE CLASS

Create `mnemosyne/stores/base.py`:

```python
"""Abstract base class for memory stores."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class MemoryStore(ABC):
    """Abstract interface for all storage backends (PostgreSQL, SQLite, etc.)."""

    @abstractmethod
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
        """Insert or update a note. Returns note ID."""
        pass

    @abstractmethod
    def delete_note(self, title: str, vault_path: str) -> bool:
        """Delete a note by title."""
        pass

    @abstractmethod
    def search_semantic(
        self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Vector similarity search."""
        pass

    @abstractmethod
    def search_keyword(self, query: str, top_k: int = 10) -> List[Dict]:
        """Full-text search."""
        pass

    @abstractmethod
    def search_graph(self, note_title: str, depth: int = 2, top_k: int = 10) -> List[Dict]:
        """Graph traversal via wiki-links."""
        pass

    @abstractmethod
    def hybrid_search(
        self, query: str, query_embedding: List[float], top_k: int = 10
    ) -> List[Dict]:
        """Reciprocal Rank Fusion of semantic + keyword + salience."""
        pass

    @abstractmethod
    def update_links(self, note_id: str, wiki_links: List[str]):
        """Update graph edges."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict:
        """Get vault statistics."""
        pass
```

---

## 5. STEP 4: CREATE SQLiteStore

Create `mnemosyne/stores/sqlite.py`:

```python
"""SQLite store with pure-Python vector similarity."""

import os
import json
import math
import logging
import sqlite3
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

    def __init__(self, db_path: str = SQLITE_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._ensure_schema()

    def _conn(self):
        """Get a new SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
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
                    source_note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                    target_note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
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
                CREATE INDEX IF NOT EXISTS prospective_trigger_idx ON prospective(trigger_at);
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
        import uuid

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
                        salience = ?, embedding = ?, updated_at = datetime('now')
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
                    INSERT INTO notes (id, title, content, tags, note_type, status, salience, embedding, vault_path)
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
            return cur.rowcount > 0

    def search_semantic(
        self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Brute-force cosine similarity in Python."""
        with self._conn() as conn:
            where = "status = 'active'"
            params = []
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
        """Simple substring search (SQLite has no native full-text in default build)."""
        terms = query.lower().split()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM notes WHERE status = 'active'"
            ).fetchall()

        results = []
        for row in rows:
            text = (row["title"] + " " + row["content"]).lower()
            score = sum(1 for term in terms if term in text) / len(terms) if terms else 0
            if score > 0:
                results.append({**dict(row), "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def search_graph(self, note_title: str, depth: int = 2, top_k: int = 10) -> List[Dict]:
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

        sorted_results = sorted(
            scores.values(), key=lambda x: x["rrf_score"], reverse=True
        )
        return sorted_results[:top_k]

    def update_links(self, note_id: str, wiki_links: List[str]):
        """Update graph edges."""
        with self._conn() as conn:
            conn.execute("DELETE FROM links WHERE source_note_id = ?", (note_id,))
            for target_title in wiki_links:
                target = conn.execute(
                    "SELECT id FROM notes WHERE title = ? AND status = 'active'",
                    (target_title.strip(),),
                ).fetchone()
                if target:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO links (id, source_note_id, target_note_id, link_type)
                        VALUES (?, ?, ?, 'wiki')
                    """,
                        (str(__import__("uuid").uuid4()), note_id, target["id"]),
                    )
            conn.commit()

    def get_stats(self) -> Dict:
        """Get vault statistics."""
        with self._conn() as conn:
            note_count = conn.execute(
                "SELECT COUNT(*) FROM notes WHERE status = 'active'"
            ).fetchone()[0]
            link_count = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM prospective WHERE status = 'pending'"
            ).fetchone()[0]
            return {"notes": note_count, "links": link_count, "pending_reminders": pending}

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
```

---

## 6. STEP 5: MODIFY EXISTING FILES

### 6.1 Modify `mnemosyne/stores/__init__.py`

```python
"""Store backends with auto-detection."""

import os
import logging
from typing import Optional

from mnemosyne.stores.base import MemoryStore
from mnemosyne.stores.postgres import PgVectorStore
from mnemosyne.stores.sqlite import SQLiteStore

logger = logging.getLogger("unified-memory")

__all__ = ["MemoryStore", "PgVectorStore", "SQLiteStore", "create_store"]


def create_store(dsn: Optional[str] = None) -> MemoryStore:
    """
    Auto-detect the best available store.
    
    Priority:
    1. PostgreSQL (if dsn provided or MEMORY_DB_DSN set and connection works)
    2. SQLite (fallback, always works)
    """
    dsn = dsn or os.environ.get("MEMORY_DB_DSN")
    
    if dsn:
        try:
            store = PgVectorStore(dsn)
            logger.info(f"Using PostgreSQL store: {dsn}")
            return store
        except Exception as e:
            logger.warning(f"PostgreSQL unavailable ({e}), falling back to SQLite")
    
    sqlite_path = os.environ.get(
        "MEMORY_SQLITE_PATH",
        os.path.expanduser("~/.mnemosyne/mnemosyne.db")
    )
    logger.info(f"Using SQLite store: {sqlite_path}")
    return SQLiteStore(sqlite_path)
```

### 6.2 Modify `mnemosyne/stores/postgres.py`

Add import at top:
```python
from mnemosyne.stores.base import MemoryStore
```

Change class declaration:
```python
class PgVectorStore(MemoryStore):
```

### 6.3 Modify `mnemosyne/core.py`

Replace:
```python
from mnemosyne.stores.postgres import PgVectorStore, DB_DSN
```
With:
```python
from mnemosyne.stores import create_store
from mnemosyne.stores.postgres import DB_DSN
```

Replace in `__init__`:
```python
self.db = PgVectorStore(dsn)
```
With:
```python
self.db = create_store(dsn)
```

---

## 7. STEP 6: WRITE TESTS

Create `tests/test_sqlite.py`:

```python
import pytest
import tempfile
import os
from mnemosyne.stores.sqlite import SQLiteStore


class TestSQLiteStore:
    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStore(db_path)

    def test_upsert_and_search(self, store):
        store.upsert_note(
            "Test Note", "test content", ["tag"], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        results = store.search_keyword("test", top_k=5)
        assert len(results) > 0
        assert results[0]["title"] == "Test Note"

    def test_semantic_search(self, store):
        store.upsert_note(
            "Note A", "machine learning", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        store.upsert_note(
            "Note B", "deep learning", [], "concept", "active", 0.5,
            [0.2] * 384, "/tmp/vault"
        )
        results = store.search_semantic([0.15] * 384, top_k=2)
        assert len(results) == 2

    def test_delete_note(self, store):
        store.upsert_note(
            "Delete Me", "content", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        assert store.delete_note("Delete Me", "/tmp/vault")
        assert not store.delete_note("Delete Me", "/tmp/vault")

    def test_hybrid_search(self, store):
        store.upsert_note(
            "Note A", "machine learning", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        results = store.hybrid_search("machine", [0.1] * 384, top_k=5)
        assert len(results) > 0

    def test_graph_search(self, store):
        id1 = store.upsert_note(
            "Source", "content", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        id2 = store.upsert_note(
            "Target", "content", [], "concept", "active", 0.5,
            [0.1] * 384, "/tmp/vault"
        )
        store.update_links(id1, ["Target"])
        results = store.search_graph("Source", depth=2, top_k=5)
        assert len(results) > 0
```

Create `tests/test_store_factory.py`:

```python
import pytest
import os
from unittest.mock import patch, MagicMock
from mnemosyne.stores import create_store


class TestCreateStore:
    def test_prefers_postgresql_when_available(self):
        with patch("mnemosyne.stores.postgres.PgVectorStore") as mock_pg:
            mock_pg.return_value = MagicMock()
            store = create_store("postgresql://localhost/test")
            mock_pg.assert_called_once()

    def test_falls_back_to_sqlite(self):
        with patch("mnemosyne.stores.postgres.PgVectorStore") as mock_pg:
            mock_pg.side_effect = Exception("No PG")
            with patch("mnemosyne.stores.sqlite.SQLiteStore") as mock_sqlite:
                mock_sqlite.return_value = MagicMock()
                store = create_store("postgresql://localhost/test")
                mock_sqlite.assert_called_once()
```

---

## 8. STEP 7: UPDATE README

Add to `README.md` after the Installation section:

```markdown
## Try Without PostgreSQL!

Mnemosyne now works with SQLite — no database setup required:

```bash
pip install -e .
python -c "from mnemosyne import UnifiedMemorySystem; m = UnifiedMemorySystem()"
```

By default, if PostgreSQL is not available, Mnemosyne automatically uses SQLite
stored at `~/.mnemosyne/mnemosyne.db`. Markdown vault files still work the same way.

To force PostgreSQL, set `MEMORY_DB_DSN`:
```bash
export MEMORY_DB_DSN="postgresql://..."
```

To force SQLite, set `MEMORY_SQLITE_PATH`:
```bash
export MEMORY_SQLITE_PATH="/path/to/mnemosyne.db"
```
```

---

## 9. STEP 8: VERIFY

```bash
# Test 1: Import works
python -c "from mnemosyne.stores import create_store; print('OK')"

# Test 2: SQLite store works standalone
python -c "
from mnemosyne.stores.sqlite import SQLiteStore
s = SQLiteStore('/tmp/test_mnemosyne.db')
id = s.upsert_note('Test', 'content', ['tag'], 'concept', 'active', 0.5, [0.1]*384, '/tmp')
print('Upserted:', id)
results = s.search_keyword('content')
print('Found:', len(results))
"

# Test 3: Auto-detection works without PostgreSQL
# (make sure MEMORY_DB_DSN is NOT set)
python -c "
import os
os.environ.pop('MEMORY_DB_DSN', None)
from mnemosyne import UnifiedMemorySystem
m = UnifiedMemorySystem(auto_sync=False)
print('Store type:', type(m.db).__name__)
"

# Test 4: Run tests
make test
```

---

## 10. STEP 9: COMMIT AND PUSH

```bash
git add .
git commit -m "feat: add SQLite fallback for zero-config installs"
git push origin feature/phase-1-sqlite-fallback
```

---

## 11. STEP 10: CREATE PR

Use GitHub MCP:
- **Owner:** M4F-S
- **Repo:** mo-graphify-obsidian-memory
- **Title:** `Phase 1: SQLite Fallback — Zero-config installs`
- **Body:** 
```
## Phase 1: SQLite Fallback

This PR adds SQLite as a fallback storage backend so users can try Mnemosyne without installing PostgreSQL.

### Changes
- **Abstract interface:** Added `MemoryStore` ABC in `mnemosyne/stores/base.py`
- **SQLite store:** Added `SQLiteStore` with brute-force cosine similarity for semantic search
- **Auto-detection:** `create_store()` tries PostgreSQL first, falls back to SQLite
- **Tests:** Added `test_sqlite.py` and `test_store_factory.py`
- **Docs:** Updated README with "Try Without PostgreSQL!" section

### Key Design Decisions
- Semantic search uses pure-Python cosine similarity (brute force, fine for <10K notes)
- Keyword search uses simple substring matching (SQLite has no built-in full-text by default)
- Graph search uses BFS traversal
- Hybrid search uses same RRF formula as PostgreSQL path

### Testing
- All unit tests pass
- SQLite-specific tests added
- Store factory tests verify auto-detection logic
```
- **Base:** `develop`
- **Head:** `feature/phase-1-sqlite-fallback`

---

## CONSTRAINTS

- Do NOT modify core logic beyond what's specified
- Do NOT add new features (no MCP v2, no CLI — those are later phases)
- All code MUST pass `flake8` (use `make lint`)
- All tests MUST pass before creating PR
- Preserve backward compatibility with PostgreSQL path

---

## DEFINITION OF DONE

- [ ] `mnemosyne/stores/base.py` created with `MemoryStore` ABC
- [ ] `mnemosyne/stores/sqlite.py` created with full implementation
- [ ] `mnemosyne/stores/__init__.py` updated with `create_store()` factory
- [ ] `mnemosyne/stores/postgres.py` inherits from `MemoryStore`
- [ ] `mnemosyne/core.py` uses `create_store()` instead of `PgVectorStore`
- [ ] `tests/test_sqlite.py` passes
- [ ] `tests/test_store_factory.py` passes
- [ ] README updated with SQLite instructions
- [ ] All existing tests still pass (PostgreSQL path)
- [ ] PR created to `develop`

---

## CRITICAL NOTES

1. **The builder session before you completed Phase 0.** The code is already on `develop`. You are adding to it.
2. **Read the source code FIRST** — understand `PgVectorStore` before writing `SQLiteStore`.
3. **Both stores must have the same interface** — `UnifiedMemorySystem` should work with either without changes.
4. **Brute-force cosine is acceptable** — our target is <10K notes per user in early versions.
5. **Do NOT install psycopg2 if not needed** — SQLite path should work without it.

Start by reading the source code, then proceed step by step.
