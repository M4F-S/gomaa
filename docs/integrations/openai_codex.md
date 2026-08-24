# Integrating Mnemosyne with OpenAI Codex, Operator & Custom Agents

For custom AI CLI tools or OpenAI Function Calling pipelines:

## OpenAI Function Calling / Tool Calling Definition

```python
import openai
from mnemosyne import UnifiedMemorySystem

mem = UnifiedMemorySystem()

tools = [
    {
        "type": "function",
        "function": {
            "name": "memory_remember",
            "description": "Store important knowledge, decisions, or code patterns in persistent memory",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short unique title"},
                    "content": {"type": "string", "description": "Markdown content"},
                    "wing": {"type": "string", "description": "Domain/project scope", "default": "general"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "pinned": {"type": "boolean", "description": "Set true to make permanent and immune to decay"}
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_recall",
            "description": "Search past memory by meaning or keywords",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Semantic query"},
                    "mode": {"type": "string", "enum": ["hybrid", "semantic", "keyword", "graph"], "default": "hybrid"},
                    "top_k": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }
    }
]

def execute_tool(name: str, arguments: dict):
    if name == "memory_remember":
        return mem.remember(**arguments)
    elif name == "memory_recall":
        return mem.recall(**arguments)
    raise ValueError(f"Unknown tool: {name}")
```
