"""
CrewAI Multi-Agent Memory Adapter for Mnemosyne.
Provides scoped team-wide and agent-specific memory isolation.
"""

from typing import Any, Dict, List, Optional
from mnemosyne.core import UnifiedMemorySystem


class MnemosyneMemoryHandler:
    """
    CrewAI memory handler for multi-agent swarms.
    Maps agent roles to domain wings and tasks to rooms.
    """

    def __init__(
        self,
        memory: Optional[UnifiedMemorySystem] = None,
        crew_name: str = "crew",
    ):
        self.memory = memory or UnifiedMemorySystem()
        self.crew_name = crew_name

    def save(
        self,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        agent_role: str = "agent",
    ) -> Dict[str, Any]:
        """Save a task execution output or finding."""
        metadata = metadata or {}
        task_name = metadata.get("task", "general")
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        content_str = str(value)
        title_preview = content_str[:40].replace("\n", " ").strip()
        title = f"{agent_role.capitalize()} - {task_name.capitalize()}: {title_preview}"

        tags_combined = list(set(tags + ["crewai", self.crew_name, agent_role]))
        salience = float(metadata.get("salience", 0.6))
        pinned = bool(metadata.get("pinned", False))

        return self.memory.remember(
            title=title,
            content=content_str,
            tags=tags_combined,
            salience=salience,
            wing=self.crew_name,
            room=task_name,
            pinned=pinned,
        )

    def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.35,
        agent_role: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search memories relevant to the crew task."""
        scope = {"wing": self.crew_name} if self.crew_name != "general" else None
        results = self.memory.recall(
            query=query,
            mode="hybrid",
            top_k=limit,
            scope=scope,
        )
        return [r for r in results if r.get("score", r.get("rrf_score", 1.0)) >= score_threshold]
