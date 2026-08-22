"""Mnemosyne v3.0 MCP Server — JSON-RPC stdio transport."""

import json
import sys
import time
import signal
import logging
from typing import Dict, List

from mnemosyne.core import UnifiedMemorySystem

logger = logging.getLogger("mcp-server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class MCPServer:
    def __init__(self):
        self.memory = UnifiedMemorySystem()
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
            req_id = None
            try:
                req = json.loads(line)
                req_id = req.get("id")
                resp = self._handle(req)
                if resp is None:
                    continue
            except json.JSONDecodeError as e:
                self._error_count += 1
                resp = {"jsonrpc": "2.0", "error": {"code": -32700, "message": str(e)}, "id": req_id}
            except Exception as e:
                self._error_count += 1
                logger.error(f"[{req_id}] Unexpected error: {e}")
                resp = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": req_id}
            print(json.dumps(resp), flush=True)
        logger.info("MCP Memory Server shutting down...")

    def _setup_signal_handlers(self):
        def _handler(signum, frame):
            self._running = False
        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)

    def _handle(self, req: Dict) -> Dict:
        method = req.get("method")
        params = req.get("params", {})
        req_id = req.get("id")
        self._request_count += 1

        try:
            if req_id is None:
                return None
            if method == "ping":
                return {"jsonrpc": "2.0", "result": {}, "id": req_id}
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "serverInfo": {"name": "mnemosyne", "version": "3.0.0"},
                    },
                    "id": req_id,
                }
            if method == "tools/list":
                return {"jsonrpc": "2.0", "result": {"tools": self._tools()}, "id": req_id}
            if method == "tools/call":
                name = params.get("name", "")
                args = params.get("arguments", {})
                result = self._call_tool(name, args)
                return {
                    "jsonrpc": "2.0",
                    "result": {"content": [{"type": "text", "text": json.dumps(result, default=str)}]},
                    "id": req_id,
                }
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": req_id}
        except Exception as e:
            self._error_count += 1
            logger.error(f"[{req_id}] Tool error in {method}: {e}")
            return {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}, "id": req_id}

    def _tools(self) -> List[Dict]:
        return [
            {
                "name": "memory_remember",
                "description": "Save a fact, decision, or observation to persistent memory. Use wing/room to organize hierarchically.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short descriptive title for the memory"},
                        "content": {"type": "string", "description": "The full content to remember"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "salience": {"type": "number", "description": "Importance score 0.0-1.0"},
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
                "description": "Ingest a full conversation transcript verbatim into memory, auto-chunked.",
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
                "description": "View recent memory operations (remember, recall, remind) as a timeline.",
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
                "description": "Get memory system statistics, health check, and version info",
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
