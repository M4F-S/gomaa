from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MemoryStore(ABC):
    @abstractmethod
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
    ) -> Any:
        pass

    @abstractmethod
    def delete_note(self, title: str, vault_path: str = "") -> bool:
        pass

    @abstractmethod
    def search_semantic(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
        scope: Optional[Dict] = None,
    ) -> List[Dict]:
        pass

    @abstractmethod
    def search_keyword(self, query: str, top_k: int = 10, scope: Optional[Dict] = None) -> List[Dict]:
        pass

    @abstractmethod
    def search_graph(self, note_title: str, depth: int = 2, top_k: int = 10) -> List[Dict]:
        pass

    @abstractmethod
    def search_associative_ppr(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        scope: Optional[Dict] = None,
        restart_prob: float = 0.15,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        scope: Optional[Dict] = None,
    ) -> List[Dict]:
        pass

    @abstractmethod
    def apply_decay(self, decay_rate: float = 0.95, archive_threshold: float = 0.05) -> Dict:
        pass

    @abstractmethod
    def archive_stale(self, archive_threshold: float = 0.10, days: int = 90) -> int:
        pass

    @abstractmethod
    def update_links(self, note_id: Any, wiki_links: List[str]) -> None:
        pass

    @abstractmethod
    def reconcile_links(self) -> int:
        pass

    @abstractmethod
    def log_timeline(
        self, action: str, note_title: Optional[str] = None, query: Optional[str] = None, summary: Optional[str] = None
    ) -> None:
        pass

    @abstractmethod
    def get_timeline(self, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_note_history(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        pass

    # --- Quadrant 1: Episodic Event Ledger ---
    @abstractmethod
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
        pass

    def log_event(
        self,
        session_id: str,
        event_type: str,
        stimulus: str,
        response: str,
        turn_index: int = 1,
        origin_agent: str = "agent",
        outcome_status: str = "success",
        surprise_factor: float = 0.0,
        embedding: Optional[List[float]] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper for logging episodic events."""
        return self.log_episodic_event(
            session_id=session_id,
            turn_index=turn_index,
            origin_agent=origin_agent,
            event_type=event_type,
            stimulus=stimulus,
            response=response,
            outcome_status=outcome_status,
            surprise_factor=surprise_factor,
            embedding=embedding,
        )

    @abstractmethod
    def get_unconsolidated_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def mark_events_consolidated(self, event_ids: List[Any]) -> int:
        pass

    @abstractmethod
    def get_episodic_events(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        pass

    # --- Quadrant 2: Procedural Playbooks ---
    @abstractmethod
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
        pass

    @abstractmethod
    def search_playbooks(
        self,
        query_embedding: Optional[List[float]] = None,
        domain: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def record_playbook_execution(self, skill_name: str, success: bool) -> bool:
        pass

    @abstractmethod
    def get_playbook(self, skill_name: str) -> Optional[Dict[str, Any]]:
        pass

    # --- Quadrant 3: Working Memory Buffer ---
    @abstractmethod
    def get_working_memory(self, session_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_working_memory(
        self,
        session_id: str,
        agent_role: str,
        active_goal: Optional[str] = None,
        subtask_stack: Optional[List[Any]] = None,
        hypotheses: Optional[List[Any]] = None,
        attention_window: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def clear_working_memory(self, session_id: str) -> bool:
        pass

    # --- Weighted Graph Links & Graph Topology ---
    @abstractmethod
    def add_weighted_link(
        self,
        source_id: Any,
        target_id: Any,
        relation_type: str = "associative",
        weight: float = 1.0,
    ) -> bool:
        pass

    @abstractmethod
    def get_graph_adjacency(self) -> Dict[str, List[Dict[str, Any]]]:
        pass

    # --- Epistemic Conflicts & Truth Maintenance (ATMS) ---
    @abstractmethod
    def log_conflict(self, old_note_id: Any, new_note_id: Any, conflict_description: str) -> int:
        pass

    @abstractmethod
    def get_pending_conflicts(self, limit: int = 20) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def resolve_conflict_supersede(self, old_id: Any, new_id: Any, resolved_by: str = "system") -> bool:
        pass
