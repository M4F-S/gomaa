"""
LangChain & LangGraph Memory Adapter for Mnemosyne.
Provides drop-in memory variables loading, context assembly, and turn persistence.
"""

from typing import Any, Dict, List, Optional
from mnemosyne.core import UnifiedMemorySystem


class MnemosyneMemory:
    """
    Drop-in LangChain / LangGraph memory adapter.
    Uses Mnemosyne's hybrid search and token-budgeted context assembler.
    """

    def __init__(
        self,
        memory: Optional[UnifiedMemorySystem] = None,
        memory_key: str = "history",
        input_key: str = "input",
        output_key: str = "output",
        max_tokens: int = 2000,
        wing: str = "langchain",
        room: str = "chat",
        salience: float = 0.6,
        return_messages: bool = False,
    ):
        self.memory = memory or UnifiedMemorySystem()
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.max_tokens = max_tokens
        self.wing = wing
        self.room = room
        self.salience = salience
        self.return_messages = return_messages

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load assembled memory context for the incoming prompt."""
        query = str(inputs.get(self.input_key, ""))
        if not query and inputs:
            query = " ".join(str(v) for v in inputs.values() if isinstance(v, str))

        if not query:
            return {self.memory_key: "" if not self.return_messages else []}

        scope = {"wing": self.wing, "room": self.room} if self.wing != "general" else None
        context_data = self.memory.assemble_context(
            query=query,
            max_tokens=self.max_tokens,
            scope=scope,
            mode="hybrid",
        )

        context_str = context_data.get("context_text", "")
        if self.return_messages:
            return {self.memory_key: [{"role": "system", "content": context_str}]}
        return {self.memory_key: context_str}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Save a user/assistant turn into Mnemosyne."""
        input_str = str(inputs.get(self.input_key, ""))
        output_str = str(outputs.get(self.output_key, ""))

        if not input_str and not output_str:
            return

        title_preview = input_str[:40].replace("\n", " ").strip() or "Turn"
        title = f"{self.room.capitalize()} Turn: {title_preview}"
        content = f"### User\n{input_str}\n\n### Assistant\n{output_str}"

        self.memory.remember(
            title=title,
            content=content,
            tags=["dialog", self.wing, self.room],
            salience=self.salience,
            wing=self.wing,
            room=self.room,
        )

    def clear(self) -> None:
        """Clear memory is a no-op for durable persistent memory to avoid accidental data loss."""
        pass
