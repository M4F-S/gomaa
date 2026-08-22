---
title: "Decision: Use GitHub + Memory Vault for Persistence"
date: 2026-07-07
tags: [decision, tooling, git, persistence]
type: decision
salience: 0.9
links: []
---

# Decision: Use GitHub + Memory Vault for Persistence

## Context

Context compression means we lose decisions after 20-30 tool calls. We need a way to persist:
1. Architectural decisions
2. Session summaries
3. Issues and bugs found
4. Roadmap and plans

## Decision

We use TWO persistence mechanisms:

### 1. GitHub (Code and Docs)

- Repository: `github.com/M4F-S/mo-graphify-obsidian-memory`
- Stores: code, tests, docs, README, CI/CD config
- Push after every successful phase
- Branch: `main` (production), `develop` (integration), `feature/*` (features)

### 2. Memory Vault (Decisions and Session Logs)

- Location: `~/Documents/Kimi/Workspaces/Mnemosyne/obsidian-vault/`
- Format: Markdown files with YAML frontmatter
- Structure:
  ```
  obsidian-vault/
  ├── decisions/        # Architectural decisions
  ├── sessions/         # Session summaries
  ├── issues/           # Bugs and issues
  ├── reviews/          # Pre-build reviews and audits
  ├── roadmap/          # Roadmap versions
  └── *.md             # Regular notes
  ```
- Syncs to PostgreSQL for search, but files are source of truth

### Vault-to-GitHub Sync Protocol (Added in v1.1)

After each phase, sync decisions from vault to repo:

```bash
# Copy new decisions from vault to repo
cp ~/Documents/Kimi/Workspaces/Mnemosyne/obsidian-vault/decisions/* docs/decisions/
cp ~/Documents/Kimi/Workspaces/Mnemosyne/obsidian-vault/sessions/* docs/sessions/
cp ~/Documents/Kimi/Workspaces/Mnemosyne/obsidian-vault/reviews/* docs/reviews/

# Commit and push
git add docs/decisions/ docs/sessions/ docs/reviews/
git commit -m "docs: sync decisions and session logs from vault"
git push origin develop
```

**Rationale:** The vault is searchable and linked (wiki-links), but GitHub is versioned and collaborative. Both are needed.

## Why Both?

- GitHub: For code, collaboration, version control, CI/CD
- Memory Vault: For decisions that need to survive context compression and be searchable
- The vault is also the product (Mnemosyne uses its own vault for its own memory)

## Rationale

GitHub alone doesn't solve context compression - READMEs and docs are static. The memory vault allows us to:
- Search decisions by topic ("show me all decisions about database")
- Link decisions to each other (wiki-links)
- See the history of a decision (temporal)
- Have the system remember what we decided (dogfooding our own product)

## Consequences

- Positive: Decisions are searchable, linked, persistent
- Negative: Two places to maintain (GitHub + vault)
- Mitigation: The vault is the product - we're dogfooding. GitHub is for code only. Sync protocol automates the duplication.

## Status: ACCEPTED

## Date: 2026-07-07 (updated from 2026-07-06)
## Version: 1.1
