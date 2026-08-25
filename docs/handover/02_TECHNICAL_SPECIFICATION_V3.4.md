# Mnemosyne Technical Specification (v3.4.0) 🔬

---

## 1. Storage Topologies

### 1.1 PostgreSQL + pgvector (Production Fleet)

Each agent connects to its private database (`toy_db`, `old_db`, `candy_db`, `pencil_db`, `trader_db`) plus the optional global fleet database (`shared_db`).

#### Core Schema
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    note_type TEXT DEFAULT 'concept',
    status TEXT DEFAULT 'active',
    salience FLOAT DEFAULT 0.5,
    embedding vector(384),
    vault_path TEXT,
    wing TEXT DEFAULT 'general',
    room TEXT DEFAULT 'general',
    origin_agent TEXT DEFAULT 'local',
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT notes_title_vault_unique UNIQUE (title, vault_path)
);

-- High-Recall HNSW Vector Index (vector_cosine_ops)
CREATE INDEX IF NOT EXISTS notes_embedding_hnsw_idx 
ON notes USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- GIN Full-Text Search Index (Weighted Title: A, Content: B)
CREATE INDEX IF NOT EXISTS idx_notes_fts 
ON notes USING gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')));

-- Hierarchical Scoping Index
CREATE INDEX IF NOT EXISTS idx_notes_scope ON notes (wing, room, status);
CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes USING gin(tags);

-- Bi-Directional Knowledge Graph Links
CREATE TABLE IF NOT EXISTS links (
    id SERIAL PRIMARY KEY,
    source_note_id INT REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id INT REFERENCES notes(id) ON DELETE CASCADE,
    link_type TEXT DEFAULT 'wiki',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_link_pair UNIQUE (source_note_id, target_note_id)
);

-- Historical Version Snapshots
CREATE TABLE IF NOT EXISTS note_versions (
    id SERIAL PRIMARY KEY,
    note_id INT REFERENCES notes(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    salience FLOAT DEFAULT 0.5,
    version_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chronological Activity Timeline
CREATE TABLE IF NOT EXISTS timeline (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    note_title TEXT,
    query TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prospective Reminders
CREATE TABLE IF NOT EXISTS prospective (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    trigger_at TIMESTAMPTZ NOT NULL,
    recurring TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 2. Algorithms & Formulations

### 2.1 Hybrid Reciprocal Rank Fusion (RRF) Ranking

When retrieving memories, candidate sets are generated from dense semantic search, PostgreSQL full-text search, and recursive 2-hop graph traversal. Results are merged and scored via:

$$\text{RRF Score}(d) = 1.0 \times \frac{1}{60 + \text{rank}_{\text{dense}}(d)} + 0.8 \times \frac{1}{60 + \text{rank}_{\text{keyword}}(d)} + 0.6 \times \frac{1}{60 + \text{rank}_{\text{graph}}(d)} + 0.2 \times \text{Salience}(d)$$

* **Cross-Store Sorting:** Candidate memories from both private stores and `shared_db` are globally sorted by `RRF Score` before applying `top_k` truncation.

### 2.2 Ebbinghaus Exponential Memory Decay

$$Salience(t) = Salience_0 \times (0.95)^{\Delta t_{\text{days}}}$$

* **Touch Feedback:** Accessing a memory updates `last_accessed_at`, resetting its decay curve.
* **Pinned Immunity:** Notes marked with `pinned=True` or tagged `#pinned`, `#permanent`, or `#core` are exempt from decay ($Salience = 1.0$).
* **Auto-Archiving:** Consolidation automatically transitions notes with $Salience < 0.05$ and unaccessed for $>90\text{ days}$ to `status = 'archived'`.

---

## 3. Asynchronous Google Drive Sync Architecture

* **Local-First Speed:** Agent reads/writes execute directly against local SSD storage (<1ms).
* **MD5 Delta Verification:** Sync manager computes local and remote MD5 hashes to download/upload only changed files.
* **Conflict Resolution:** Concurrent edits produce sibling `NoteName.conflict-YYYYMMDD-HHMMSS.md` files, preserving data integrity without clobbering.
* **Authentication:** Supports Google Cloud Service Account JSON and OAuth2 user tokens.

---

## 4. MCP Tools Catalog (8 Tools)

1. `memory_remember(title, content, tags, wing, room, salience, pinned)`
2. `memory_publish_shared(title, content, tags, wing, room)`
3. `memory_recall(query, mode, top_k, scope, include_shared)`
4. `memory_ingest_session(transcript, wing, room)`
5. `memory_timeline(limit)`
6. `memory_history(title, limit)`
7. `memory_remind_me(title, trigger_at, content, recurring)`
8. `memory_audit()`
