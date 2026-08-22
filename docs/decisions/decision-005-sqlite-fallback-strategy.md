---
title: "Decision: SQLite Fallback Strategy (Phase 1)"
date: 2026-07-07
tags: [decision, architecture, phase-1, sqlite, database]
type: decision
salience: 0.9
links: []
---

# Decision: SQLite Fallback Strategy (Phase 1)

## Context

Phase 0 is complete. The `mnemosyne/` package works with PostgreSQL + pgvector. Phase 1 needs a zero-config fallback so users can try Mnemosyne without installing PostgreSQL.

## Decision

### 1. SQLite Vector Search: Pure-Python Cosine Similarity on BLOB Embeddings

**Rationale:** 
- `sqlite-vss` requires compiled extensions → not portable
- `sqlite-vec` is newer but still requires setup
- Brute-force cosine similarity in Python is fine for <10K notes (our target for early users)
- We already have the embedding vectors from the Embedder class

**Implementation:**
- Store embeddings as JSON BLOBs in SQLite
- For semantic search: load all embeddings, compute cosine similarity in Python
- Return top_k results
- This is a temporary solution until we need scale

**Why not skip semantic search?** User said "choose the best but do not skip"

### 2. Auto-Detection Logic: PostgreSQL First, SQLite Fallback

```python
def create_store(dsn: Optional[str] = None):
    # Try PostgreSQL first
    if dsn or os.environ.get("MEMORY_DB_DSN"):
        try:
            return PgVectorStore(dsn or os.environ.get("MEMORY_DB_DSN"))
        except Exception:
            pass  # Fall through to SQLite
    
    # Fallback to SQLite
    sqlite_path = os.environ.get(
        "MEMORY_SQLITE_PATH", 
        os.path.expanduser("~/.mnemosyne/mnemosyne.db")
    )
    return SQLiteStore(sqlite_path)
```

**User confirmed:** "okay"

### 3. Sync Strategy: Same as PostgreSQL Mode

- Markdown vault remains the source of truth
- SQLite is a rebuildable index (same role as PostgreSQL)
- `VaultManager.sync_to_db()` works with both stores via common interface
- User trusts this decision: "i dont understand but still i believe you will make the right choice"

## Interface Contract

Both `PgVectorStore` and `SQLiteStore` must implement:

```python
class MemoryStore(ABC):
    def upsert_note(...) -> str
    def delete_note(...) -> bool
    def search_semantic(embedding, top_k, filters) -> List[Dict]
    def search_keyword(query, top_k) -> List[Dict]
    def search_graph(note_title, depth, top_k) -> List[Dict]
    def hybrid_search(query, query_embedding, top_k) -> List[Dict]
    def update_links(note_id, wiki_links)
    def get_stats() -> Dict
```

## Files to Create/Modify

**New files:**
- `mnemosyne/stores/base.py` — Abstract `MemoryStore` interface
- `mnemosyne/stores/sqlite.py` — `SQLiteStore` implementation

**Modified files:**
- `mnemosyne/stores/__init__.py` — Add `create_store()` factory
- `mnemosyne/stores/postgres.py` — Inherit from `MemoryStore`
- `mnemosyne/core.py` — Use `create_store()` instead of direct `PgVectorStore`
- `mnemosyne/__init__.py` — Ensure exports work

## Exit Criteria
- [ ] `pip install -e .` works without PostgreSQL
- [ ] `UnifiedMemorySystem()` auto-detects SQLite when PostgreSQL unavailable
- [ ] `memory.remember()` and `memory.recall()` work with SQLite
- [ ] `memory.recall(query, mode="semantic")` works (via brute-force cosine)
- [ ] `memory.recall(query, mode="hybrid")` works (semantic + keyword)
- [ ] All unit tests pass (with mocked stores)
- [ ] Integration tests pass for both PostgreSQL and SQLite paths
- [ ] README updated with "Try without PostgreSQL!" section

## Status: APPROVED
## Date: 2026-07-07
