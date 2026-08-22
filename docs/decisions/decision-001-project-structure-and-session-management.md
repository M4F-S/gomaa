---
title: "Decision: Project Structure and Session Management"
date: 2026-07-06
tags: [decision, architecture, project-management, session-management]
type: decision
salience: 0.95
links: []
---

# Decision: Project Structure and Session Management

## Context

We are building Mnemosyne, an open-core local-first memory system for AI agents. The project has grown from a single script (`mo_graphify_memory.py`, 984 lines) to a vision for a full platform. We need a structured approach to avoid:

1. Context compression (losing decisions after 20-30 tool calls)
2. Overwhelming a single session with all tasks
3. Losing track of what was built and what was decided

## Decision

### 1. Separate Session Roles

| Role | Purpose | Spawned When |
|------|---------|------------|
| **Architect** (this session) | Planning, review, audit, git management, user communication | Continuous |
| **Builder** | Write code, implement features, fix bugs | Per phase |
| **Test** | Write tests, run test suite, verify coverage | After each build |
| **Docs** | README, docs, examples, blog posts | After feature complete |
| **Audit** | Security review, code quality, performance | Before release |

### 2. Session Handoff Protocol

Every builder session receives:
- Detailed prompt with scope, constraints, exit criteria
- All files it needs to modify
- Definition of done

Every builder session produces:
- HANDOFF.md file with what was built, issues found, next steps
- Git branch with clean commit history
- PR to `develop` branch

### 3. Memory Vault for Persistence

All decisions are saved to the Obsidian vault as markdown files:
- `decisions/decision-NNN-*.md` — Architectural decisions
- `sessions/session-YYYY-MM-DD-*.md` — Session summaries
- `issues/issue-NNN-*.md` — Bugs and issues found
- `roadmap/roadmap-v*.md` — Roadmap versions

This ensures decisions survive context compression.

### 4. Git Workflow

- `main` — Production-ready, protected
- `develop` — Integration branch
- `feature/phase-N-*` — Feature branches
- Commit convention: `type: description` (feat, fix, docs, test, chore)
- Push to GitHub after every successful phase

## Rationale

Without session management, a single session trying to do everything will:
- Hit context compression and lose track of decisions
- Produce lower-quality code due to fatigue
- Not be able to review its own work effectively

Separate sessions have fresh context windows and can focus on one task.

## Consequences

- Positive: Better code quality, decisions survive compression, parallel work possible
- Negative: More overhead for session spawning, need careful handoff documentation
- Mitigation: Architect session manages all handoffs, memory vault persists decisions

## Status: ACCEPTED

## Date: 2026-07-06
