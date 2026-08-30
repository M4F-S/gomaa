"""
Gomaa Embedded Web Dashboard HTTP Server.
Zero external dependencies - uses Python standard library http.server.
"""

import json
import logging
import os
import threading
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from gomaa.core import UnifiedMemorySystem

logger = logging.getLogger("gomaa-dashboard")


class DashboardRequestHandler(BaseHTTPRequestHandler):
    memory: Optional[UnifiedMemorySystem] = None
    static_dir: str = os.path.join(os.path.dirname(__file__), "static")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/dashboard", "/index.html"]:
            html_file = os.path.join(self.static_dir, "index.html")
            if os.path.exists(html_file):
                with open(html_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "Dashboard HTML not found")
                return

        if path == "/api/stats":
            stats = self.memory.stats() if self.memory else {}

            # Layer heuristics
            raw_notes = self.memory.db.search_keyword("", top_k=200) if self.memory else []
            layer_counts = {
                "episodic": 0,
                "semantic": 0,
                "procedural": 0,
                "social": 0,
                "preferential": 0,
            }

            for n in raw_notes:
                w = (n.get("wing") or "").lower()
                r = (n.get("room") or "").lower()
                tags = [t.lower() for t in (n.get("tags") or [])]
                all_tokens = set([w, r] + tags)

                if any(k in all_tokens for k in ["session", "sessions", "episodic", "dialog", "turn", "history"]):
                    layer_counts["episodic"] += 1
                elif any(k in all_tokens for k in ["rule", "rules", "policy", "procedural", "guide", "sop", "pinned"]):
                    layer_counts["procedural"] += 1
                elif any(k in all_tokens for k in ["user", "social", "contact", "person", "team", "collaborator"]):
                    layer_counts["social"] += 1
                elif any(
                    k in all_tokens for k in ["preference", "preferential", "config", "setting", "style", "taste"]
                ):
                    layer_counts["preferential"] += 1
                else:
                    layer_counts["semantic"] += 1

            data = {
                "system": {
                    "version": "3.5.0",
                    "status": "healthy",
                    "backend": self.memory.db.__class__.__name__ if self.memory else "None",
                    "vault_path": str(self.memory.vault.vault_path) if self.memory else "None",
                },
                "stats": stats,
                "layers": layer_counts,
                "total_notes": len(raw_notes),
            }
            self._send_json(data)
            return

        if path == "/api/notes":
            raw_notes = self.memory.db.search_keyword("", top_k=150) if self.memory else []
            notes_data = []
            for n in raw_notes:
                notes_data.append(
                    {
                        "id": n.get("id"),
                        "title": n.get("title"),
                        "wing": n.get("wing", "general"),
                        "room": n.get("room", "general"),
                        "salience": n.get("salience", 0.5),
                        "pinned": n.get("pinned", False),
                        "tags": n.get("tags", []),
                        "created_at": n.get("created_at"),
                    }
                )
            self._send_json({"notes": notes_data})
            return

        if path == "/api/timeline":
            events = self.memory.timeline(limit=30) if self.memory else []
            self._send_json({"timeline": events})
            return

        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"

        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            payload = {}

        if path == "/api/search":
            query = payload.get("query", "")
            mode = payload.get("mode", "hybrid")
            top_k = int(payload.get("top_k", 5))
            scope = payload.get("scope")

            results = (
                self.memory.recall(
                    query=query,
                    mode=mode,
                    top_k=top_k,
                    scope=scope,
                )
                if self.memory
                else []
            )
            self._send_json({"query": query, "mode": mode, "results": results})
            return

        if path == "/api/assemble-context":
            query = payload.get("query", "")
            max_tokens = int(payload.get("max_tokens", 1500))
            scope = payload.get("scope")

            res = (
                self.memory.assemble_context(
                    query=query,
                    max_tokens=max_tokens,
                    scope=scope,
                )
                if self.memory
                else {}
            )
            self._send_json(res)
            return

        if path == "/api/remember":
            title = payload.get("title")
            content = payload.get("content")
            tags = payload.get("tags", [])
            salience = float(payload.get("salience", 0.5))
            wing = payload.get("wing", "general")
            room = payload.get("room", "general")
            pinned = bool(payload.get("pinned", False))

            if not title or not content:
                self._send_json({"success": False, "error": "Title and content are required"}, status=400)
                return

            res = (
                self.memory.remember(
                    title=title,
                    content=content,
                    tags=tags,
                    salience=salience,
                    wing=wing,
                    room=room,
                    pinned=pinned,
                )
                if self.memory
                else {"success": False, "error": "No memory instance"}
            )
            self._send_json(res)
            return

        self.send_error(404, "Endpoint not found")

    def log_message(self, format, *args):
        # Silence default request logging to avoid cluttering agent stdio
        pass


def create_dashboard_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    memory: Optional[UnifiedMemorySystem] = None,
) -> HTTPServer:
    DashboardRequestHandler.memory = memory or UnifiedMemorySystem()
    server = HTTPServer((host, port), DashboardRequestHandler)
    return server


def run_dashboard(
    host: str = "127.0.0.1",
    port: int = 8765,
    memory: Optional[UnifiedMemorySystem] = None,
    open_browser: bool = True,
):
    mem = memory or UnifiedMemorySystem()
    DashboardRequestHandler.memory = mem
    server = HTTPServer((host, port), DashboardRequestHandler)

    url = f"http://{host}:{port}/dashboard"
    print("=" * 65)
    print("🧠 Gomaa Knowledge Graph Dashboard")
    print("=" * 65)
    print(f"🌐 Dashboard URL: {url}")
    print(f"💾 Storage Mode:  {mem.db.__class__.__name__}")
    print(f"📁 Vault Path:    {mem.vault.vault_path}")
    print("=" * 65)
    print("Press Ctrl+C to stop the dashboard server.\n")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")
    finally:
        server.server_close()
