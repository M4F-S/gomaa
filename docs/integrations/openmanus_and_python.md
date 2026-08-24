# Integrating Mnemosyne with Open-Manus & Python Agent Frameworks

[Open-Manus](https://github.com/mannaandpoem/OpenManus), CrewAI, LangChain, AutoGen, and Smolagents can use Mnemosyne as a persistent hierarchical memory engine.

---

## 1. Open-Manus Tool Integration

In Open-Manus, tools inherit from `BaseTool`. You can add `MnemosyneTool` into `app/tool/`:

```python
# app/tool/memory_tool.py
from app.tool.base import BaseTool
from mnemosyne import UnifiedMemorySystem
import os

class MnemosyneRecallTool(BaseTool):
    name: str = "memory_recall"
    description: str = (
        "Search through persistent long-term memory for past tasks, user preferences, "
        "and architectural documentation. Input is a search query string."
    )
    
    def __init__(self):
        super().__init__()
        self._memory = UnifiedMemorySystem(
            vault_path=os.getenv("MEMORY_VAULT_PATH", "~/.manus/vault"),
            dsn=os.getenv("MEMORY_DB_DSN")
        )

    async def execute(self, query: str, **kwargs) -> str:
        results = self._memory.recall(query, top_k=5, mode="hybrid")
        if not results:
            return "No matching memories found."
        
        output = ["### Retrieved Memories:"]
        for r in results:
            output.append(f"#### {r['title']} (Score: {r.get('rrf_score', 0):.2f})\n{r['content']}\n")
        return "\n".join(output)

class MnemosyneRememberTool(BaseTool):
    name: str = "memory_remember"
    description: str = "Save crucial facts, code snippets, or solutions into long-term memory."

    def __init__(self):
        super().__init__()
        self._memory = UnifiedMemorySystem(
            vault_path=os.getenv("MEMORY_VAULT_PATH", "~/.manus/vault"),
            dsn=os.getenv("MEMORY_DB_DSN")
        )

    async def execute(self, title: str, content: str, wing: str = "general", tags: list = None, **kwargs) -> str:
        res = self._memory.remember(title=title, content=content, wing=wing, tags=tags or ["manus"])
        return f"Successfully saved memory: {title} (ID: {res.get('note_id')})"
```

---

## 2. CrewAI Integration

```python
from crewai.tools import tool
from mnemosyne import UnifiedMemorySystem

mem = UnifiedMemorySystem()

@tool("Recall Agent Knowledge")
def recall_memory(query: str) -> str:
    """Useful to search long-term memory for previous research and findings."""
    results = mem.recall(query, top_k=3, mode="hybrid")
    return "\n\n".join([f"**{r['title']}**:\n{r['content']}" for r in results])

@tool("Remember Key Finding")
def remember_finding(title: str, content: str, domain: str = "research") -> str:
    """Store critical findings or final deliverables into persistent memory."""
    mem.remember(title, content, wing=domain, tags=["crewai"])
    return f"Saved finding: {title}"
```

---

## 3. LangChain / LangGraph Integration

```python
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from mnemosyne import UnifiedMemorySystem

mem = UnifiedMemorySystem()

class RecallInput(BaseModel):
    query: str = Field(description="Search query to lookup relevant long-term memory")
    wing: str = Field(default="general", description="Project or domain wing scope")

def recall_fn(query: str, wing: str = "general"):
    return mem.recall(query, top_k=4, scope={"wing": wing})

langchain_recall_tool = StructuredTool.from_function(
    func=recall_fn,
    name="memory_recall",
    description="Query agent long-term memory with hybrid semantic + keyword search",
    args_schema=RecallInput
)
```
