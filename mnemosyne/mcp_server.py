"""Mnemosyne v3.0 MCP Server — JSON-RPC stdio transport."""

import os
import sys

# Silence Hugging Face, tokenizers, and PyTorch from writing to stdout
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import json
import time
import signal
import logging
from typing import Dict, List, Optional

from mnemosyne.core import UnifiedMemorySystem

logger = logging.getLogger("mcp-server")
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


class MCPServer:
    def __init__(self, memory: Optional[UnifiedMemorySystem] = None):
        self.memory = memory if memory is not None else UnifiedMemorySystem()
        self._running = True
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._setup_signal_handlers()

    def _uptime(self) -> float:
        return time.time() - self._start_time

    def run(self):
        logger.info("MCP Memory Server v3.0 starting...")
        for line in sys.stdin:
            if not self._running:
                break
            line = line.strip()
            if not line:
                continue
            self._request_count += 1
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
            print(json.dumps(resp), flush=True)
        logger.info("MCP Memory Server shutting down...")

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        self._running = False

    def _handle(self, req: Dict) -> Dict:
        self._request_count += 1
        method = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "mnemosyne", "version": "3.0.0"},
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
                "description": "Store a memory note in the vault with semantic embedding, tags, and hierarchical wing/room scope.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short, unique title for the memory"},
                        "content": {"type": "string", "description": "The memory content in markdown"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Categorical tags"},
                        "salience": {"type": "number", "description": "Importance score 0.0-1.0 (default 0.5)"},
                        "wing": {"type": "string", "description": "Project/domain grouping (e.g. ecommerce, security, devops)", "default": "general"},
                        "room": {"type": "string", "description": "Topic within the wing (e.g. woocommerce, firewall, docker)", "default": "general"},
                    },
                    "required": ["title", "content"],
                },
            },
            {
                "name": "memory_recall",
                "description": "Search memory by semantic meaning, keywords, or graph. Use scope to restrict to a wing/room.",
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
                "name": "memory_audit",
                "description": "Get memory system statistics, health check, active wings, and version info",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def _call_tool(self, name: str, args: Dict) -> Dict:
        if name == "memory_remember":
            return self.memory.remember(
                title=args.get("title", ""),
                content=args.get("content", ""),
                tags=args.get("tags", []),
                salience=args.get("salience"),
                wing=args.get("wing", "general"),
                room=args.get("room", "general"),
            )
        elif name == "memory_recall":
            return {
                "results": self.memory.recall(
                    query=args.get("query", ""),
                    mode=args.get("mode", "hybrid"),
                    top_k=args.get("top_k", 5),
                    scope=args.get("scope"),
                )
            }
        elif name == "memory_ingest_session":
            return self.memory.ingest_session(
                transcript=args.get("transcript", ""),
                wing=args.get("wing", "general"),
                room=args.get("room", "sessions"),
            )
        elif name == "memory_timeline":
            return {"timeline": self.memory.timeline(limit=args.get("limit", 20))}
        elif name == "memory_history":
            return {"versions": self.memory.history(
                title=args.get("title", ""),
                limit=args.get("limit", 10),
            )}
        elif name == "memory_remind_me":
            return {
                "reminder_id": self.memory.remind_me(
                    title=args.get("title", ""),
                    trigger_at=args.get("trigger_at", ""),
                    content=args.get("content", ""),
                    recurring=args.get("recurring"),
                )
            }
        elif name == "memory_audit":
            stats = self.memory.stats()
            stats["health"] = self._health()
            return stats
        else:
            return {"error": f"Unknown tool: {name}"}

    def _health(self) -> Dict:
        store_type = type(self.memory.db).__name__
        embedder_provider = self.memory.embedder._provider or "unknown"
        return {
            "server": {
                "status": "healthy",
                "version": "3.0.0",
                "uptime_seconds": round(self._uptime(), 2),
                "requests": self._request_count,
                "errors": self._error_count,
            },
            "store": {"type": store_type, "vault_path": str(self.memory.vault.vault_path)},
            "embedder": {
                "provider": embedder_provider,
                "model": self.memory.embedder.model_name,
                "dimension": self.memory.embedder.dim,
            },
        }

# Backwards compatibility alias
MemoryMCPServer = MCPServer
