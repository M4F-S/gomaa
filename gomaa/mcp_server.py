"""
MCP Server for Gomaa Unified Memory Platform (v3.5.0).
Exposes memory tools over standard MCP JSON-RPC protocol via stdio.
"""

import json
import logging
import os
import signal
import sys
import time
from typing import Any, Dict, List, Optional

from . import __version__
from .core import UnifiedMemorySystem

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("gomaa-mcp")


class MCPServer:
    def __init__(self, memory: Optional[UnifiedMemorySystem] = None):
        self.memory = memory or UnifiedMemorySystem()
        self._running = True
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._setup_signal_handlers()

    def run(self):
        logger.info(f"MCP Memory Server v{__version__} starting...")
        for line in sys.stdin:
            if not self._running:
                break
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self._handle(req)
            except json.JSONDecodeError:
                self._error_count += 1
                resp = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
            except Exception as e:
                self._error_count += 1
                req_id = req.get("id") if "req" in locals() and isinstance(req, dict) else None
                logger.error(f"[{req_id}] Unexpected error: {e}")
                resp = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": req_id}
            try:
                print(json.dumps(resp), flush=True)
            except (BrokenPipeError, IOError):
                break
        logger.info("MCP Memory Server shutting down...")

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        self._running = False

    def _handle(self, req: Any) -> Dict:
        self._request_count += 1
        if not isinstance(req, dict):
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: Expected JSON object"},
                "id": None,
            }

        method = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "gomaa", "version": __version__},
                },
                "id": req_id,
            }
        elif method == "notifications/initialized":
            return {}
        elif method == "ping":
            return {"jsonrpc": "2.0", "result": {}, "id": req_id}
        elif method == "tools/list":
            return {"jsonrpc": "2.0", "result": {"tools": self._get_tools()}, "id": req_id}
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                result = self._call_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]
                    },
                    "id": req_id,
                }
            except Exception as e:
                self._error_count += 1
                logger.error(f"Tool call failed [{tool_name}]: {e}")
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                        "isError": True,
                    },
                    "id": req_id,
                }
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": req_id,
            }

    def _get_tools(self) -> List[Dict]:
        return [
            {
                "name": "memory_remember",
                "description": "Store a private memory note in the vault with semantic embedding, tags, and hierarchical wing/room scope.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short, unique title for the memory"},
                        "content": {"type": "string", "description": "The memory content in markdown"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Categorical tags"},
                        "salience": {"type": "number", "description": "Importance score 0.0-1.0 (default 0.5)"},
                        "wing": {"type": "string", "description": "Project/domain grouping (e.g. ecommerce, security, devops)", "default": "general"},
                        "room": {"type": "string", "description": "Topic within the wing (e.g. woocommerce, firewall, docker)", "default": "general"},
                        "pinned": {"type": "boolean", "description": "Set true to make permanently immune to Ebbinghaus temporal decay", "default": False},
                    },
                    "required": ["title", "content"],
                },
            },
            {
                "name": "memory_publish_shared",
                "description": "Publish a sanitized, curated finding or policy to the cross-agent shared fleet memory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title for the shared policy or finding"},
                        "content": {"type": "string", "description": "The shared knowledge content in markdown (must not contain private credentials)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
                        "wing": {"type": "string", "default": "shared"},
                        "room": {"type": "string", "default": "general"},
                    },
                    "required": ["title", "content"],
                },
            },
            {
                "name": "memory_recall",
                "description": "Search memory by semantic meaning, keywords, or graph. Retrieves from both private and shared stores.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "mode": {"type": "string", "enum": ["hybrid", "semantic", "keyword", "graph"]},
                        "top_k": {"type": "integer", "default": 5},
                        "scope": {
                            "type": "object",
                            "description": "Restrict search to a wing and/or room",
                            "properties": {
                                "wing": {"type": "string"},
                                "room": {"type": "string"},
                            },
                        },
                        "include_shared": {"type": "boolean", "default": True, "description": "Whether to include cross-agent shared fleet memory"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "memory_ingest_session",
                "description": "Ingest a full conversation transcript verbatim into memory, split along conversational turn boundaries.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": "The full conversation text to ingest"},
                        "wing": {"type": "string", "default": "general"},
                        "room": {"type": "string", "default": "sessions"},
                    },
                    "required": ["transcript"],
                },
            },
            {
                "name": "memory_timeline",
                "description": "View recent memory operations (remember, recall, remind, consolidate) as a chronological timeline.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
            {
                "name": "memory_history",
                "description": "View version history of a specific memory note (previous edits).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "The title of the note to check history for"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["title"],
                },
            },
            {
                "name": "memory_remind_me",
                "description": "Schedule a future reminder or recurring task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "trigger_at": {"type": "string"},
                        "recurring": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                    },
                    "required": ["title", "trigger_at"],
                },
            },
            {
                "name": "memory_assemble_context",
                "description": "Retrieve and format high-salience memories into a strict token-budgeted XML prompt block ready for direct agent context injection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query to retrieve context for"},
                        "max_tokens": {"type": "integer", "default": 2000, "description": "Maximum token budget for the assembled context"},
                        "mode": {"type": "string", "enum": ["hybrid", "semantic", "keyword", "graph"], "default": "hybrid"},
                        "scope": {
                            "type": "object",
                            "description": "Optional wing/room filter scope",
                            "properties": {
                                "wing": {"type": "string"},
                                "room": {"type": "string"},
                            },
                        },
                        "include_shared": {"type": "boolean", "default": True, "description": "Whether to include shared fleet knowledge"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "memory_audit",
                "description": "Get memory system statistics, health check, active wings, and version info",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def _call_tool(self, name: str, args: Dict) -> Any:
        args = args or {}
        if name == "memory_remember":
            if "title" not in args or "content" not in args:
                raise ValueError("Missing required arguments: 'title' and 'content' are required for memory_remember.")
            return self.memory.remember(
                title=args["title"],
                content=args["content"],
                tags=args.get("tags"),
                salience=args.get("salience", 0.5),
                wing=args.get("wing", "general"),
                room=args.get("room", "general"),
                pinned=args.get("pinned", False),
            )
        elif name == "memory_publish_shared":
            if "title" not in args or "content" not in args:
                raise ValueError("Missing required arguments: 'title' and 'content' are required for memory_publish_shared.")
            return self.memory.publish_shared(
                title=args["title"],
                content=args["content"],
                tags=args.get("tags"),
                wing=args.get("wing", "shared"),
                room=args.get("room", "general"),
            )
        elif name == "memory_recall":
            if "query" not in args:
                raise ValueError("Missing required argument: 'query' is required for memory_recall.")
            results = self.memory.recall(
                query=args["query"],
                mode=args.get("mode", "hybrid"),
                top_k=args.get("top_k", 5),
                scope=args.get("scope"),
                include_shared=args.get("include_shared", True),
            )
            return {"results": results}
        elif name == "memory_assemble_context":
            if "query" not in args:
                raise ValueError("Missing required argument: 'query' is required for memory_assemble_context.")
            return self.memory.assemble_context(
                query=args["query"],
                max_tokens=args.get("max_tokens", 2000),
                scope=args.get("scope"),
                mode=args.get("mode", "hybrid"),
                include_shared=args.get("include_shared", True),
            )
        elif name == "memory_ingest_session":
            if "transcript" not in args:
                raise ValueError("Missing required argument: 'transcript' is required for memory_ingest_session.")
            return self.memory.ingest_session(
                transcript=args["transcript"],
                wing=args.get("wing", "general"),
                room=args.get("room", "sessions"),
            )
        elif name == "memory_timeline":
            return {"timeline": self.memory.timeline(limit=args.get("limit", 20))}
        elif name == "memory_history":
            if "title" not in args:
                raise ValueError("Missing required argument: 'title' is required for memory_history.")
            return {"history": self.memory.note_history(title=args["title"], limit=args.get("limit", 10))}
        elif name == "memory_remind_me":
            if "title" not in args or "trigger_at" not in args:
                raise ValueError("Missing required arguments: 'title' and 'trigger_at' are required for memory_remind_me.")
            return self.memory.remind_me(
                title=args["title"],
                content=args.get("content", ""),
                trigger_at=args["trigger_at"],
                recurring=args.get("recurring"),
            )
        elif name == "memory_audit":
            return {
                "stats": self.memory.stats(),
                "health": self._health(),
            }
        else:
            return {"error": f"Unknown tool: {name}"}

    def _health(self) -> Dict[str, Any]:
        return {
            "server": {
                "name": "gomaa",
                "version": __version__,
                "status": "healthy",
                "uptime_seconds": round(self._uptime(), 2),
                "requests_served": self._request_count,
                "error_count": self._error_count,
            },
            "store": {
                "backend": getattr(self.memory.db, "__class__", type(self.memory.db)).__name__,
                "vault_path": getattr(self.memory.vault, "vault_path", None),
                "shared_store": bool(self.memory.shared_db),
            },
            "embedder": {
                "provider": getattr(self.memory.embedder, "_provider", "unknown"),
                "model": getattr(self.memory.embedder, "model_name", "unknown"),
                "dim": getattr(self.memory.embedder, "dim", 384),
                "remote_url": getattr(self.memory.embedder, "embed_url", None),
            },
        }

    def _uptime(self) -> float:
        return time.time() - self._start_time


def main():
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
