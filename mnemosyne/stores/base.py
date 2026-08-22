"""Abstract base class for memory stores."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class MemoryStore(ABC):
    """Abstract interface for all storage backends (PostgreSQL, SQLite, etc.)."""

    @abstractmethod
    def upsert_note(
        self,
        title: str,
        content: str,
        tags: List[str],
        note_type: str,
        status: str,
        salience: float,
        embedding: List[float],
        vault_path: str,
    ) -> str:
        """Insert or update a note. Returns note ID."""
        pass

    @abstractmethod
    def delete_note(self, title: str, vault_path: str) -> bool:
        """Delete a note by title."""
        pass

    @abstractmethod
    def search_semantic(
        self, query_embedding: List[float], top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Vector similarity search."""
        pass

    @abstractmethod
    def search_keyword(self, query: str, top_k: int = 10) -> List[Dict]:
        """Full-text search."""
        pass

    @abstractmethod
    def search_graph(self, note_title: str, depth: int = 2,
                     top_k: int = 10) -> List[Dict]:
        """Graph traversal via wiki-links."""
        pass

    @abstractmethod
    def hybrid_search(
        self, query: str, query_embedding: List[float], top_k: int = 10
    ) -> List[Dict]:
        """Reciprocal Rank Fusion of semantic + keyword + salience."""
        pass

    @abstractmethod
    def update_links(self, note_id: str, wiki_links: List[str]) -> None:
        """Update graph edges."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """Get vault statistics."""
        pass
