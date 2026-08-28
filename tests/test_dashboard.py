import json
import threading
import time
import urllib.request
import pytest

from mnemosyne.core import UnifiedMemorySystem
from mnemosyne.dashboard.server import create_dashboard_server


@pytest.fixture
def dashboard_server(tmp_path):
    vault_path = str(tmp_path / "dash_vault")
    db_path = f"sqlite://{tmp_path / 'dash_test.db'}"
    mem = UnifiedMemorySystem(vault_path=vault_path, dsn=db_path, auto_sync=False)

    # Pre-populate sample notes across layers
    mem.remember("Turn 1 Session", "User asked about API keys", tags=["session", "dialog"], wing="sessions", room="general")
    mem.remember("Production Rule", "Never commit .env secrets", tags=["rule", "policy"], wing="security", room="guidelines", pinned=True)
    mem.remember("User Contact", "DevOps lead: Alice (alice@example.com)", tags=["user", "team"], wing="team", room="contacts")
    mem.remember("Editor Style", "Prefers 4 spaces indent", tags=["preference", "config"], wing="preferences", room="ide")
    mem.remember("FastAPI Guide", "Async endpoints with Pydantic schemas", tags=["python", "fastapi"], wing="engineering", room="backend")

    server = create_dashboard_server(host="127.0.0.1", port=18765, memory=mem)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    time.sleep(0.2)
    yield "http://127.0.0.1:18765"

    server.shutdown()
    server.server_close()


class TestDashboardServer:
    def test_get_dashboard_html(self, dashboard_server):
        url = f"{dashboard_server}/dashboard"
        with urllib.request.urlopen(url) as response:
            assert response.status == 200
            content = response.read().decode("utf-8")
            assert "<!DOCTYPE html>" in content
            assert "Mnemosyne" in content
            assert "5 Cognitive Memory Layers" in content

    def test_get_api_stats(self, dashboard_server):
        url = f"{dashboard_server}/api/stats"
        with urllib.request.urlopen(url) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert data["system"]["status"] == "healthy"
            assert "layers" in data
            assert data["layers"]["episodic"] >= 1
            assert data["layers"]["procedural"] >= 1
            assert data["layers"]["social"] >= 1
            assert data["layers"]["preferential"] >= 1
            assert data["layers"]["semantic"] >= 1

    def test_get_api_notes(self, dashboard_server):
        url = f"{dashboard_server}/api/notes"
        with urllib.request.urlopen(url) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert "notes" in data
            assert len(data["notes"]) >= 5

    def test_post_api_search(self, dashboard_server):
        url = f"{dashboard_server}/api/search"
        payload = json.dumps({"query": "FastAPI", "mode": "hybrid", "top_k": 3}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert "results" in data
            assert len(data["results"]) >= 1
            assert any("FastAPI" in r["title"] for r in data["results"])

    def test_post_api_assemble_context(self, dashboard_server):
        url = f"{dashboard_server}/api/assemble-context"
        payload = json.dumps({"query": "Production Rule secrets", "max_tokens": 1000}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert "context_text" in data
            assert "<memory_context>" in data["context_text"]
            assert "Production Rule" in data["context_text"]

    def test_post_api_remember(self, dashboard_server):
        url = f"{dashboard_server}/api/remember"
        payload = json.dumps({
            "title": "New Dashboard Note",
            "content": "Created from browser dashboard",
            "tags": ["dashboard", "test"],
            "wing": "general",
            "room": "web",
            "salience": 0.9,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert data.get("success") is True
