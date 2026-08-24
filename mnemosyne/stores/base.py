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
        self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None, scope: Optional[Dict] = None,
    ) -> List[Dict]:
        pass

    @abstractmethod
    def search_keyword(self, query: str, top_k: int = 10, scope: Optional[Dict] = None) -> List[Dict]:
        pass

    @abstractmethod
    def search_graph(self, note_title: str, depth: int = 2, top_k: int = 10) -> List[Dict]:
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
    def update_links(self, note_id: Any, wiki_links: List[str]) -> None:
        pass

    @abstractmethod
    def reconcile_links(self) -> int:
        pass

    @abstractmethod
    def log_timeline(self, action: str, note_title: Optional[str] = None, query: Optional[str] = None, summary: Optional[str] = None) -> None:
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
