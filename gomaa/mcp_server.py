"""
MCP Server for Gomaa Unified Memory Platform (v4.0.0 - Gomaa Neo).
Exposes memory tools over standard MCP JSON-RPC protocol via stdio.
"""

import json
import logging
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


def _safe_int(val: Any, default: int) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_bool(val: Any, default: bool) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "t")
    return bool(val)


def _safe_tags(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(item) for item in val]
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except Exception:
                pass
        return [t.strip() for t in val.split(",") if t.strip()]
    return [str(val)]


def _safe_list(val: Any, default: Optional[List] = None) -> Optional[List]:
    if val is None:
        return default
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return [t.strip() for t in val.split(",") if t.strip()]
    return [val]


def _safe_dict(val: Any, default: Optional[Dict] = None) -> Optional[Dict]:
    if val is None:
        return default
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("{") and val.endswith("}"):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    return default


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
            if resp is not None:
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

    def _handle(self, req: Any) -> Optional[Dict]:
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
        elif method == "notifications/initialized" or (isinstance(method, str) and method.startswith("notifications/")):
            return None
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
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]},
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
                        "wing": {
                            "type": "string",
                            "description": "Project/domain grouping (e.g. ecommerce, security, devops)",
                            "default": "general",
                        },
                        "room": {
                            "type": "string",
                            "description": "Topic within the wing (e.g. woocommerce, firewall, docker)",
                            "default": "general",
                        },
                        "pinned": {
                            "type": "boolean",
                            "description": "Set true to make permanently immune to Ebbinghaus temporal decay",
                            "default": False,
                        },
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
                        "content": {
                            "type": "string",
                            "description": "The shared knowledge content in markdown (must not contain private credentials)",
                        },
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
                        "mode": {
                            "type": "string",
                            "enum": ["hybrid", "semantic", "keyword", "graph", "associative_ppr", "procedural", "episodic"],
                            "default": "hybrid",
                            "description": "Recall mode: hybrid RRF, dense semantic, keyword BM25, 2-hop graph walk, HippoRAG associative PPR, procedural playbooks, or episodic turns.",
                        },
                        "top_k": {"type": "integer", "default": 5},
                        "scope": {
                            "type": "object",
                            "description": "Restrict search to a wing and/or room",
                            "properties": {
                                "wing": {"type": "string"},
                                "room": {"type": "string"},
                            },
                        },
                        "include_shared": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to include cross-agent shared fleet memory",
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
                "name": "memory_assemble_context",
                "description": "Retrieve and format high-salience memories into a strict token-budgeted XML prompt block ready for direct agent context injection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query to retrieve context for"},
                        "max_tokens": {
                            "type": "integer",
                            "default": 2000,
                            "description": "Maximum token budget for the assembled context",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["hybrid", "semantic", "keyword", "graph", "associative_ppr"],
                            "default": "hybrid",
                        },
                        "scope": {
                            "type": "object",
                            "description": "Optional wing/room filter scope",
                            "properties": {
                                "wing": {"type": "string"},
                                "room": {"type": "string"},
                            },
                        },
                        "include_shared": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to include shared fleet knowledge",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "memory_ingest_event",
                "description": "Log an episodic turn or experiential event into the biological episodic ledger with surprise rating and outcome.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Active session or conversation ID"},
                        "stimulus": {"type": "string", "description": "The input stimulus, query, or prompt"},
                        "response": {"type": "string", "description": "The agent's response, action, or output"},
                        "event_type": {
                            "type": "string",
                            "enum": ["dialogue", "tool_call", "observation", "internal_thought"],
                            "default": "dialogue",
                        },
                        "tool_name": {"type": "string", "description": "Optional name of tool executed"},
                        "tool_args": {"type": "object", "description": "Optional tool arguments"},
                        "surprise_factor": {
                            "type": "number",
                            "description": "Surprise rating 0.0-1.0 (>=0.5 triggers sleep crystallization)",
                            "default": 0.0,
                        },
                        "outcome_status": {
                            "type": "string",
                            "enum": ["success", "failure", "partial"],
                            "default": "success",
                        },
                    },
                    "required": ["session_id", "stimulus", "response"],
                },
            },
            {
                "name": "memory_save_playbook",
                "description": "Store or update a procedural skill playbook with preconditions, tool sequences, and error recovery.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "skill_name": {"type": "string", "description": "Unique identifier for the procedural skill"},
                        "domain": {"type": "string", "description": "Skill domain (e.g. devops, pentest, data, coding)"},
                        "description": {"type": "string", "description": "Functional description of when and how to execute this skill"},
                        "preconditions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required preconditions or environment state",
                        },
                        "tool_sequence": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Ordered sequence of steps or tool invocations",
                        },
                        "error_recovery": {
                            "type": "object",
                            "description": "Fallback strategies or recovery policies",
                        },
                    },
                    "required": ["skill_name", "domain", "description"],
                },
            },
            {
                "name": "memory_sleep",
                "description": "Trigger biological sleep consolidation: SWS episodic crystallization, REM swarm playbook sharing, and synaptic homeostasis.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "decay_factor": {
                            "type": "number",
                            "default": 0.95,
                            "description": "Temporal decay multiplier per sleep cycle",
                        },
                        "archive_threshold": {
                            "type": "number",
                            "default": 0.10,
                            "description": "Salience cutoff below which stale inactive memories are archived",
                        },
                    },
                },
            },
            {
                "name": "memory_working_buffer",
                "description": "Manage bounded working memory scratchpad, active goals, hypothesis state, and attention focus for a session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["get", "update", "clear"],
                            "description": "Working memory action",
                        },
                        "session_id": {"type": "string", "description": "Session identifier"},
                        "agent_role": {"type": "string", "default": "agent"},
                        "active_goal": {"type": "string", "description": "Primary goal currently pursued"},
                        "subtask_stack": {"type": "array", "description": "Stack of active subtasks"},
                        "hypotheses": {"type": "array", "description": "Candidate hypotheses under evaluation"},
                        "attention_window": {"type": "array", "description": "Top items currently within attention span"},
                    },
                    "required": ["action", "session_id"],
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
                title=str(args["title"]),
                content=str(args["content"]),
                tags=_safe_tags(args.get("tags")),
                salience=_safe_float(args.get("salience"), 0.5),
                wing=str(args.get("wing", "general")),
                room=str(args.get("room", "general")),
                pinned=_safe_bool(args.get("pinned"), False),
            )
        elif name == "memory_publish_shared":
            if "title" not in args or "content" not in args:
                raise ValueError(
                    "Missing required arguments: 'title' and 'content' are required for memory_publish_shared."
                )
            return self.memory.publish_shared(
                title=str(args["title"]),
                content=str(args["content"]),
                tags=_safe_tags(args.get("tags")),
                wing=str(args.get("wing", "shared")),
                room=str(args.get("room", "general")),
            )
        elif name == "memory_recall":
            if "query" not in args:
                raise ValueError("Missing required argument: 'query' is required for memory_recall.")
            results = self.memory.recall(
                query=str(args["query"]),
                mode=str(args.get("mode", "hybrid")),
                top_k=_safe_int(args.get("top_k"), 5),
                scope=_safe_dict(args.get("scope"), None),
                include_shared=_safe_bool(args.get("include_shared"), True),
            )
            return {"results": results}
        elif name == "memory_assemble_context":
            if "query" not in args:
                raise ValueError("Missing required argument: 'query' is required for memory_assemble_context.")
            return self.memory.assemble_context(
                query=str(args["query"]),
                max_tokens=_safe_int(args.get("max_tokens"), 2000),
                scope=_safe_dict(args.get("scope"), None),
                mode=str(args.get("mode", "hybrid")),
                include_shared=_safe_bool(args.get("include_shared"), True),
            )
        elif name == "memory_ingest_session":
            if "transcript" not in args:
                raise ValueError("Missing required argument: 'transcript' is required for memory_ingest_session.")
            return self.memory.ingest_session(
                transcript=str(args["transcript"]),
                wing=str(args.get("wing", "general")),
                room=str(args.get("room", "sessions")),
            )
        elif name == "memory_timeline":
            return {"timeline": self.memory.timeline(limit=_safe_int(args.get("limit"), 20))}
        elif name == "memory_history":
            if "title" not in args:
                raise ValueError("Missing required argument: 'title' is required for memory_history.")
            return {
                "history": self.memory.note_history(title=str(args["title"]), limit=_safe_int(args.get("limit"), 10))
            }
        elif name == "memory_remind_me":
            if "title" not in args or "trigger_at" not in args:
                raise ValueError(
                    "Missing required arguments: 'title' and 'trigger_at' are required for memory_remind_me."
                )
            return self.memory.remind_me(
                title=str(args["title"]),
                content=str(args.get("content", "")),
                trigger_at=str(args["trigger_at"]),
                recurring=str(args["recurring"]) if args.get("recurring") else None,
            )
        elif name == "memory_audit":
            return {
                "stats": self.memory.stats(),
                "health": self._health(),
            }
        elif name == "memory_ingest_event":
            if "session_id" not in args or "stimulus" not in args or "response" not in args:
                raise ValueError(
                    "Missing required arguments: 'session_id', 'stimulus', and 'response' are required for memory_ingest_event."
                )
            return self.memory.log_event(
                session_id=str(args["session_id"]),
                event_type=str(args.get("event_type", "dialogue")),
                stimulus=str(args["stimulus"]),
                response=str(args["response"]),
                tool_name=str(args["tool_name"]) if args.get("tool_name") else None,
                tool_args=_safe_dict(args.get("tool_args"), None),
                surprise_factor=_safe_float(args.get("surprise_factor"), 0.0),
                outcome_status=str(args.get("outcome_status", "success")),
            )
        elif name == "memory_save_playbook":
            if "skill_name" not in args or "domain" not in args or "description" not in args:
                raise ValueError(
                    "Missing required arguments: 'skill_name', 'domain', and 'description' are required for memory_save_playbook."
                )
            return self.memory.upsert_playbook(
                skill_name=str(args["skill_name"]),
                domain=str(args["domain"]),
                description=str(args["description"]),
                preconditions=_safe_tags(args.get("preconditions")),
                tool_sequence=_safe_list(args.get("tool_sequence"), []) or [],
                error_recovery=_safe_dict(args.get("error_recovery"), {}) or {},
            )
        elif name == "memory_sleep":
            return self.memory.sleep(
                decay_rate=_safe_float(args.get("decay_factor"), 0.95),
                archive_threshold=_safe_float(args.get("archive_threshold"), 0.10),
            )
        elif name == "memory_working_buffer":
            if "action" not in args or "session_id" not in args:
                raise ValueError(
                    "Missing required arguments: 'action' and 'session_id' are required for memory_working_buffer."
                )
            action = str(args["action"]).lower()
            sid = str(args["session_id"])
            if action == "get":
                return {"session_id": sid, "working_memory": self.memory.get_working_memory(sid)}
            elif action == "clear":
                success = self.memory.clear_working_memory(sid)
                return {"session_id": sid, "cleared": success}
            elif action == "update":
                return self.memory.update_working_memory(
                    session_id=sid,
                    agent_role=str(args.get("agent_role", "agent")),
                    active_goal=str(args["active_goal"]) if args.get("active_goal") is not None else None,
                    subtask_stack=_safe_list(args.get("subtask_stack"), None),
                    hypotheses=_safe_list(args.get("hypotheses"), None),
                    attention_window=_safe_list(args.get("attention_window"), None),
                )
            else:
                raise ValueError(f"Invalid working memory action: {action}")
        else:
            raise ValueError(f"Unknown tool: {name}")

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
