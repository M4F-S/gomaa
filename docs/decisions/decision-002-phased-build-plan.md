---
title: "Decision: Phased Build Plan"
date: 2026-07-06
tags: [decision, architecture, roadmap, build-plan]
type: decision
salience: 0.95
links: []
---

# Decision: Phased Build Plan

## Context

We have a working 984-line Python script (`mo_graphify_memory.py`) with core memory functionality. We need to turn it into a proper package, add tests, add CI/CD, and make it installable. The user wants to keep ALL features but build incrementally.

## Decision

We will build in 7 phases, each delivering a shippable increment:

| Phase | Weeks | Goal | Deliverable |
|-------|-------|------|-------------|
| **Phase 0** | 1-2 | Foundation | `pip install -e .` works, tests pass, CI green |
| **Phase 1** | 2-3 | SQLite Fallback | Zero-config installs, no PostgreSQL required |
| **Phase 2** | 3-4 | MCP v2 | Stateless MCP spec, works with Claude/Cursor |
| **Phase 3** | 4-5 | CLI | `mnemosyne remember`, `mnemosyne recall` commands |
| **Phase 4** | 5-6 | VPS Deploy | Docker Compose, HTTPS, remote MCP access |
| **Phase 5** | 7-8 | Launch | Hacker News, 42 Berlin, 100 stars |
| **Phase 6** | Month 3 | Connectors | GitHub, Slack, file import |
| **Phase 7** | Month 4-6 | Advanced | Graph viz, web dashboard, salience v2 |

## Rationale

The user wants to keep all features but build incrementally. Each phase adds value:
- Phase 0: The repo is a proper package (anyone can install)
- Phase 1: Anyone can try it without PostgreSQL (lower barrier)
- Phase 2: Claude/Cursor users can connect (developer audience)
- Phase 3: CLI users can use it from terminal (daily workflow)
- Phase 4: VPS means shared memory for teams (collaboration)
- Phase 5: Launch gets users and feedback (traction)
- Phase 6: Connectors make it useful (real workflows)
- Phase 7: Advanced features make it sticky (retention)

## Consequences

- Positive: Each phase is shippable, user can stop at any phase and still have value
- Negative: Some features (plugin marketplace, multi-agent, TEE) are deferred to Year 2
- Mitigation: The core architecture (microkernel, plugins) is designed in Phase 0 so future features can be added without rewriting

## Status: ACCEPTED

## Date: 2026-07-06
