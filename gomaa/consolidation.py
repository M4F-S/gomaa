"""Consolidation engine for Gomaa v4.0 (Sleep & Dream biological maintenance)."""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("unified-memory-consolidation")


class ConsolidationEngine:
    """
    Biological Sleep & Dream Consolidation Engine:
    - Phase 1 (SWS): Episodic-to-semantic crystallization & procedural playbook extraction
    - Phase 2 (REM): Associative graph link formation & swarm playbook sharing
    - Phase 3 (Synaptic Homeostasis): Epistemic truth maintenance (ATMS) & adaptive pruning
    """

    def __init__(self, db, vault, embedder, shared_db=None):
        self.db = db
        self.vault = vault
        self.embedder = embedder
        self.shared_db = shared_db

    def run(self, decay_factor: float = 0.95, archive_threshold: float = 0.10) -> Dict[str, Any]:
        """Run full 3-phase biological sleep consolidation. Returns stats."""
        logger.info("Initiating Gomaa v4.0 Sleep Consolidation cycle...")

        # Phase 1: Slow-Wave Sleep (SWS) - Crystallization
        sws_stats = self._phase_sws_crystallize()

        # Phase 2: REM Associative Synthesis
        rem_stats = self._phase_rem_associative_synthesis()

        # Phase 3: Synaptic Homeostasis & Truth Maintenance (ATMS)
        homeostasis_stats = self._phase_synaptic_homeostasis(archive_threshold)

        relinked = self._rebuild_links()

        stats = {
            "archived": homeostasis_stats.get("archived", 0),
            "relinked": relinked,
            "crystallized_episodes": sws_stats.get("crystallized_episodes", 0),
            "synthesized_playbooks": sws_stats.get("synthesized_playbooks", 0),
            "discovered_links": rem_stats.get("discovered_links", 0),
            "shared_playbooks": rem_stats.get("shared_playbooks", 0),
            "conflicts_resolved": homeostasis_stats.get("conflicts_resolved", 0),
        }
        logger.info(f"Consolidation complete: {stats}")
        return stats

    def _phase_sws_crystallize(self) -> Dict[str, int]:
        """
        Phase 1: Replay unconsolidated episodic turns.
        - Extract semantic summaries from episode clusters.
        - Compile successful tool call sequences into procedural playbooks.
        - Mark episodic events as consolidated.
        """
        if not hasattr(self.db, "get_unconsolidated_events"):
            return {"crystallized_episodes": 0, "synthesized_playbooks": 0}

        events = self.db.get_unconsolidated_events(limit=100)
        if not events:
            return {"crystallized_episodes": 0, "synthesized_playbooks": 0}

        processed_event_ids = []
        crystallized_count = 0
        playbook_count = 0

        # Group events by session_id
        session_groups: Dict[str, List[Dict[str, Any]]] = {}
        for ev in events:
            sid = ev.get("session_id", "default")
            if sid not in session_groups:
                session_groups[sid] = []
            session_groups[sid].append(ev)

        for sid, group in session_groups.items():
            # 1. Procedural extraction: successful tool calls
            tool_turns = [e for e in group if e.get("event_type") == "tool_call" and e.get("outcome_status") == "success"]
            if len(tool_turns) >= 2 and hasattr(self.db, "upsert_playbook"):
                skill_name = f"skill_{sid[:8]}_{len(tool_turns)}_steps"
                tool_sequence = [
                    {"step": i + 1, "stimulus": t.get("stimulus"), "response": t.get("response")[:120]}
                    for i, t in enumerate(tool_turns)
                ]
                desc = f"Consolidated playbook from session {sid}: {tool_turns[0].get('stimulus')[:60]}"
                emb = self.embedder.embed_query(desc) if self.embedder else None
                try:
                    self.db.upsert_playbook(
                        skill_name=skill_name,
                        domain="general",
                        description=desc,
                        preconditions=["session_consolidated"],
                        tool_sequence=tool_sequence,
                        error_recovery={"retry": "linear_backoff"},
                        embedding=emb,
                    )
                    playbook_count += 1
                except Exception as e:
                    logger.warning(f"Failed upserting procedural playbook from session {sid}: {e}")

            # 2. Semantic crystallization: turns with high surprise
            high_surprise_turns = [e for e in group if float(e.get("surprise_factor", 0.0)) >= 0.5]
            if high_surprise_turns and hasattr(self.db, "upsert_note"):
                vault_path_str = str(getattr(self.vault, "vault_path", "")) if self.vault else ""
                for h in high_surprise_turns:
                    title = f"Crystallized - {h.get('stimulus')[:30].strip()}"
                    content = f"Event Stimulus:\n{h.get('stimulus')}\n\nOutcome / Response:\n{h.get('response')}"
                    emb = self.embedder.embed_query(f"{title} {content}") if self.embedder else None
                    try:
                        if self.vault and hasattr(self.vault, "write_note"):
                            try:
                                self.vault.write_note(
                                    title=title,
                                    content=content,
                                    tags=["crystallized", "sws_replay"],
                                    note_type="concept",
                                    status="active",
                                    salience=0.8,
                                    links=[],
                                    wing="general",
                                    room="crystallized",
                                )
                            except Exception as ve:
                                logger.debug(f"Vault write during SWS crystallization skipped: {ve}")
                        self.db.upsert_note(
                            title=title,
                            content=content,
                            tags=["crystallized", "sws_replay"],
                            salience=0.8,
                            embedding=emb,
                            vault_path=vault_path_str,
                            wing="general",
                            room="crystallized",
                            memory_type="semantic",
                            episodic_parent_hash=h.get("content_hash"),
                        )
                        crystallized_count += 1
                    except Exception as e:
                        logger.warning(f"Failed crystallizing semantic note: {e}")

            processed_event_ids.extend([e["id"] for e in group])

        if processed_event_ids and hasattr(self.db, "mark_events_consolidated"):
            self.db.mark_events_consolidated(processed_event_ids)

        return {
            "crystallized_episodes": len(processed_event_ids),
            "synthesized_playbooks": playbook_count,
        }

    def _phase_rem_associative_synthesis(self) -> Dict[str, int]:
        """
        Phase 2: REM sleep associative link discovery & swarm playbook dissemination.
        - Discovers latent associative links between notes in knowledge graph.
        - Shares non-credentialed high-performing procedural playbooks to shared_db.
        """
        discovered_links = 0
        shared_playbooks = 0

        # 1. Latent associative link formation between unlinked related notes
        if (
            hasattr(self.db, "search_keyword")
            and hasattr(self.db, "add_weighted_link")
            and hasattr(self.db, "get_graph_adjacency")
        ):
            try:
                candidates = self.db.search_keyword("a", top_k=30) or self.db.search_keyword("e", top_k=30)
                adj = self.db.get_graph_adjacency()
                ignore_tags = {"crystallized", "sws_replay", "pinned", "session", "transcript", "chunk", "shared"}
                for i in range(len(candidates)):
                    for j in range(i + 1, len(candidates)):
                        n1, n2 = candidates[i], candidates[j]
                        if n1["id"] == n2["id"]:
                            continue
                        existing_targets = {e["target_title"] for e in adj.get(n1["title"], [])}
                        if n2["title"] in existing_targets:
                            continue
                        t1 = set(n1.get("tags") or []) - ignore_tags
                        t2 = set(n2.get("tags") or []) - ignore_tags
                        shared_tags = t1 & t2
                        if shared_tags:
                            self.db.add_weighted_link(
                                source_id=n1["id"],
                                target_id=n2["id"],
                                relation_type="rem_associative",
                                weight=round(min(1.5, 0.7 + 0.2 * len(shared_tags)), 2),
                            )
                            discovered_links += 1
            except Exception as e:
                logger.warning(f"REM latent link discovery skipped: {e}")

        # 2. Swarm playbook dissemination
        if self.shared_db and hasattr(self.db, "search_playbooks") and hasattr(self.shared_db, "upsert_playbook"):
            try:
                local_playbooks = self.db.search_playbooks(limit=10)
                for pb in local_playbooks:
                    if pb.get("bayesian_success_rate", 0.0) >= 0.60:
                        desc = pb.get("description", "")
                        seq = str(pb.get("tool_sequence", ""))
                        if not self._has_credentials(desc) and not self._has_credentials(seq):
                            self.shared_db.upsert_playbook(
                                skill_name=pb["skill_name"],
                                domain=pb["domain"],
                                description=pb["description"],
                                preconditions=pb["preconditions"],
                                tool_sequence=pb["tool_sequence"],
                                error_recovery=pb["error_recovery"],
                                embedding=pb.get("embedding"),
                            )
                            shared_playbooks += 1
            except Exception as e:
                logger.warning(f"Swarm playbook sharing failed: {e}")

        return {"discovered_links": discovered_links, "shared_playbooks": shared_playbooks}

    def _phase_synaptic_homeostasis(self, archive_threshold: float = 0.10) -> Dict[str, int]:
        """
        Phase 3: Epistemic truth maintenance (ATMS) & active forgetting.
        - Resolves pending epistemic conflicts by superseding older notes.
        - Archives stale, low-salience memories.
        """
        conflicts_resolved = 0
        if hasattr(self.db, "get_pending_conflicts") and hasattr(self.db, "resolve_conflict_supersede"):
            try:
                pending = self.db.get_pending_conflicts(limit=20)
                for c in pending:
                    self.db.resolve_conflict_supersede(
                        old_id=c["old_note_id"],
                        new_id=c["new_note_id"],
                        resolved_by="dream_consolidation",
                    )
                    conflicts_resolved += 1
            except Exception as e:
                logger.warning(f"Conflict resolution notice: {e}")

        archived = self._archive_stale(archive_threshold)
        return {"archived": archived, "conflicts_resolved": conflicts_resolved}

    def _has_credentials(self, text: str) -> bool:
        """Sanitization regex guard."""
        patterns = [
            r"-----BEGIN (RSA|OPENSSH|PGP|PRIVATE|EC|DSA) KEY-----",
            r"(eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})",
            r"(ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{40,})",
            r"(sk-ant-api\d\d-[a-zA-Z0-9_\-]{50,}|sk-ant-[a-zA-Z0-9_\-]{20,})",
            r"(AIza[0-9A-Za-z_\-]{30,35})",
            r"(sk-[a-zA-Z0-9]{32,}|sk-proj-[a-zA-Z0-9_\-]{40,})",
        ]
        return any(re.search(p, text) for p in patterns)

    def _archive_stale(self, archive_threshold: float = 0.10) -> int:
        """Archive notes not updated in 90 days with salience below threshold."""
        if hasattr(self.db, "archive_stale"):
            return self.db.archive_stale(archive_threshold=archive_threshold, days=90)
        return 0

    def _rebuild_links(self) -> int:
        """Rebuild graph edges from vault notes via store-native reconciliation."""
        if hasattr(self.db, "reconcile_links"):
            return self.db.reconcile_links()
        return 0
