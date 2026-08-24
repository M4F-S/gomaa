# Mnemosyne Technical Specification (v3.1) 📐

---

## 1. Storage Schema

### PostgreSQL Schema (`pgvector`)
```sql
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
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tsv tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'B')
    ) STORED,
    CONSTRAINT notes_title_vault_unique UNIQUE (title, vault_path)
);

CREATE INDEX IF NOT EXISTS notes_embedding_idx ON notes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
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
```

---

## 2. Hybrid Reciprocal Rank Fusion (RRF) Ranking

When an agent queries `memory_recall`, candidates are pulled from 3 retrieval channels and merged:

$$\text{RRF Score}(d) = 1.0 \times \frac{1}{60 + \text{rank}_{\text{semantic}}(d)} + 0.8 \times \frac{1}{60 + \text{rank}_{\text{keyword}}(d)} + 0.6 \times \frac{1}{60 + \text{rank}_{\text{graph}}(d)} + 0.2 \times \text{Salience}(d)$$

---

## 3. Ebbinghaus Temporal Decay & Pinned Immunity

Every night at 03:00 AM, the decay engine updates inactive notes:

$$S_t = S_0 \times (0.95)^{\Delta t_{\text{days}}}$$

* **Archive Threshold:** If $S_t < 0.05$, the note is marked `status = 'archived'`.
* **Pinned Immunity:** Notes are **immune to decay** if:
  * Tagged `pinned`, `permanent`, or `core`
  * Created with `pinned=True`
  * Initial salience $S_0 \ge 1.0$

---

## 4. MCP Stdio Protocol Protection

* Stdio standard strictly reserves `sys.stdout` for single-line JSON-RPC messages.
* `os.environ["TOKENIZERS_PARALLELISM"] = "false"` and `os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"` prevent HuggingFace / PyTorch stdout corruption.
* All application logging is directed to `sys.stderr`.
