# Gomaa v4.0.0 (Mnemosyne Neo) Specification 🧠⚡

**Release:** v4.0.0 (Mnemosyne Neo)  
**Status:** Production Ready  
**Verification:** 115 / 115 Tests Passing (100% Success Rate across 32 Test Modules)  

---

## 1. Executive Summary

Gomaa v4.0.0 transforms Gomaa from a passive long-term vector/keyword storage tool into an active, biologically-grounded **Cognitive Quadrant Memory System** equipped with **HippoRAG 2 Associative Personalized PageRank Retrieval**, **3-Phase Biological Sleep Consolidation**, and **Epistemic Truth Maintenance (ATMS)**.

---

## 2. The Four Memory Quadrants

| Quadrant | Brain Analogue | Storage Subsystem | Capabilities |
|---|---|---|---|
| **Quadrant 1: Episodic Event Ledger** | Hippocampal Episodic Buffer | `episodic_events` | Immutable chronological turns, stimulus/response pairs, surprise factor scoring, content hashes |
| **Quadrant 2: Procedural Skill Playbooks** | Striatum & Basal Ganglia | `procedural_playbooks` | Executable tool sequences, preconditions, error recovery, Bayesian success rate tracking ($S_{bayesian} = \frac{k+1}{n+2}$) |
| **Quadrant 3: Working Memory Buffer** | Prefrontal Cortex (dlPFC) | `working_memory` | Strict $7 \pm 2$ bounded scratchpad, subtask execution stack, hypothesis tracking, attention window |
| **Quadrant 4: Semantic Knowledge Graph** | Neocortex | `notes` & `links` | Human-readable Obsidian Vault markdown, bi-directional weighted wikilinks, ATMS supersedes links |

---

## 3. HippoRAG 2 Associative Retrieval Engine

Unlike naive dense vector search (which suffers from semantic drift, polysemy, and zero topological hops), Gomaa v4.0 implements a self-contained **Personalized PageRank (PPR)** engine diffusing associative activation across weighted graph edges.

### Mathematical Formulation
$$\mathbf{p}^{(t+1)} = (1 - \alpha) \mathbf{W}_{\text{row-norm}} \mathbf{p}^{(t)} + \alpha \mathbf{p}^{(0)}$$
- Teleportation probability $\alpha = 0.15$
- Power iterations $K = 20$ (converges in $<2\text{ms}$)
- Restart distribution $\mathbf{p}^{(0)}$ seeded from top dense cosine similarity scores
- Edge weights: Associative (1.0), Hierarchical (1.5), Supersedes (2.0)

### 4-Stream Hybrid Ranking
$$RRF(d) = \sum_{m \in \{dense, bm25, hipporag\}} \frac{w_m}{60 + r_m(d)} + \Delta_{ACT-R}(d)$$
Where:
- $w_{dense} = 1.0$
- $w_{bm25} = 0.8$
- $w_{hipporag} = 1.2$
- $\Delta_{ACT-R}(d) = 0.05 \times \ln(1 + \text{access\_count}) \times e^{-0.05 \times \Delta t_{days}}$

---

## 4. Biological Sleep & Dream Consolidation Engine

Gomaa v4.0 introduces an automated 3-phase consolidation cycle modeled on mammalian sleep architecture:

1. **Slow-Wave Sleep (SWS) - Replay & Crystallization:**
   - Replays unconsolidated episodic events ($O(1)$ batch processing).
   - High surprise turns ($\ge 0.5$) crystallize into semantic knowledge notes linked via `episodic_parent_hash`.
   - Successful multi-step tool call trajectories compile into procedural playbooks.
   - Marks processed events as consolidated.

2. **REM Sleep - Associative Synthesis & Swarm Telepathy:**
   - Traverses knowledge graph to discover latent associative links.
   - Disseminates high-performing procedural playbooks ($\text{Bayesian Rate} \ge 0.60$) to `shared_db` with automated regex credential shielding.

3. **Synaptic Homeostasis - Active Forgetting & Truth Maintenance:**
   - Resolves pending Assumption-Based Truth Maintenance (ATMS) contradictions, marking outdated notes as `deprecated` and pointing `superseded_by` to the current belief.
   - Applies geometric step decay ($S_{t+1} = S_t \times d$) and archives stale, low-salience memories while preserving pinned memories.

---

## 5. Model Context Protocol (MCP) Tool Reference (13 Tools)

| Tool Name | Parameters | Description |
|---|---|---|
| `memory_remember` | `title, content, tags, wing, room, salience, pinned` | Write hierarchical notes to Obsidian vault + pgvector/SQLite. |
| `memory_publish_shared` | `title, content, tags, wing, room` | Publish sanitized findings to shared fleet memory. |
| `memory_recall` | `query, mode, top_k, scope, include_shared` | 7 search modes: `hybrid`, `semantic`, `keyword`, `graph`, `associative_ppr`, `procedural`, `episodic`. |
| `memory_assemble_context` | `query, max_tokens, scope, mode, include_shared` | Pack memories into token-budgeted prompt context block. |
| `memory_ingest_session` | `transcript, wing, room` | Turn-based transcript ingestion with sliding-window chunking. |
| `memory_timeline` | `limit` | Chronological audit trail. |
| `memory_history` | `title, limit` | Note version history & diffs. |
| `memory_remind_me` | `title, trigger_at, content, recurring` | Prospective reminder engine. |
| `memory_audit` | *(none)* | Real-time system health & backend statistics. |
| `memory_ingest_event` | `session_id, stimulus, response, event_type, surprise_factor, outcome_status, tool_name, tool_args` | Log episodic turn into experiential memory ledger. |
| `memory_save_playbook` | `skill_name, domain, description, preconditions, tool_sequence, error_recovery` | Store or update procedural skill playbook. |
| `memory_sleep` | `decay_factor, archive_threshold` | Trigger 3-phase biological consolidation cycle. |
| `memory_working_buffer` | `action, session_id, agent_role, active_goal, subtask_stack, hypotheses, attention_window` | Manage bounded working memory scratchpad. |

---

## 6. Benchmarks & Verification

The suite includes 3 dedicated cognitive benchmark tests (`tests/benchmarks/test_memory_benchmarks.py`):
1. **LoCoMo Multi-Hop Association:** Validates Personalized PageRank diffusion across an A -> B -> C -> D chain, verifying topological reachability.
2. **ATMS Contradiction Resolution:** Validates belief supercession, deprecation of invalidated notes, and verification that only active truths are recalled.
3. **Selective Forgetting & Ebbinghaus Decay:** Validates that ephemeral notes decay and archive below threshold while pinned notes resist decay permanently.
