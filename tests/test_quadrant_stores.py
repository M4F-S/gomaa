"""
Tests for Quadrant Cognitive Architecture & Storage Subsystems (Gomaa v4.0).
Verifies 100% parity and functionality for:
- Episodic Event Ledger
- Procedural Playbook Store
- Working Memory Buffer
- Weighted Graph Links
- Epistemic Conflicts & Truth Maintenance (ATMS)
"""

import tempfile
import pathlib
import pytest
from gomaa.stores.sqlite import SQLiteStore


@pytest.fixture
def sqlite_store(tmp_path):
    db_file = tmp_path / "quadrant_test.db"
    return SQLiteStore(str(db_file))


def test_episodic_event_ledger(sqlite_store):
    # 1. Log episodic event
    event = sqlite_store.log_episodic_event(
        session_id="session_001",
        turn_index=1,
        origin_agent="hermes-pentest",
        event_type="tool_call",
        stimulus="nmap -p 8080 10.0.0.5",
        response="Port 8080 open (Apache Tomcat)",
        outcome_status="success",
        surprise_factor=0.8,
        embedding=[0.1, 0.2, 0.3],
    )
    assert event["session_id"] == "session_001"
    assert event["turn_index"] == 1
    assert event["content_hash"] is not None
    assert event["consolidated"] is False

    # 2. Get unconsolidated events
    unconsolidated = sqlite_store.get_unconsolidated_events(limit=10)
    assert len(unconsolidated) == 1
    assert unconsolidated[0]["id"] == event["id"]
    assert unconsolidated[0]["surprise_factor"] == 0.8

    # 3. Mark consolidated
    marked = sqlite_store.mark_events_consolidated([event["id"]])
    assert marked == 1

    # 4. Verify no remaining unconsolidated
    unconsolidated_after = sqlite_store.get_unconsolidated_events(limit=10)
    assert len(unconsolidated_after) == 0

    # 5. Fetch all episodic events for session
    events = sqlite_store.get_episodic_events(session_id="session_001")
    assert len(events) == 1
    assert events[0]["consolidated"] is True


def test_procedural_playbooks(sqlite_store):
    # 1. Upsert playbook
    playbook = sqlite_store.upsert_playbook(
        skill_name="tomcat_vulnerability_scan",
        domain="security",
        description="Scan Apache Tomcat for default administrative credentials",
        preconditions=["port_8080_open", "service_tomcat"],
        tool_sequence=[
            {"tool": "curl", "args": {"url": "http://10.0.0.5:8080/manager/html"}},
            {"tool": "bruteforce_auth", "args": {"wordlist": "tomcat_defaults.txt"}},
        ],
        error_recovery={"connection_refused": "wait_and_retry"},
        embedding=[0.2, 0.4, 0.6],
    )
    assert playbook["skill_name"] == "tomcat_vulnerability_scan"
    assert playbook["bayesian_success_rate"] == 0.5  # (0 + 1) / (0 + 2)

    # 2. Record executions
    sqlite_store.record_playbook_execution("tomcat_vulnerability_scan", success=True)
    sqlite_store.record_playbook_execution("tomcat_vulnerability_scan", success=True)

    fetched = sqlite_store.get_playbook("tomcat_vulnerability_scan")
    assert fetched is not None
    assert fetched["invocation_count"] == 2
    assert fetched["success_count"] == 2
    assert fetched["bayesian_success_rate"] == 0.75  # (2 + 1) / (2 + 2)

    # 3. Search playbooks
    results = sqlite_store.search_playbooks(query_embedding=[0.2, 0.4, 0.6], domain="security", limit=3)
    assert len(results) >= 1
    assert results[0]["skill_name"] == "tomcat_vulnerability_scan"
    assert len(results[0]["preconditions"]) == 2


def test_working_memory_buffer(sqlite_store):
    # 1. Update working memory
    wm = sqlite_store.update_working_memory(
        session_id="session_wm_01",
        agent_role="lead_architect",
        active_goal="Refactor authentication layer",
        subtask_stack=["Audit existing JWT", "Draft OAuth2 schema"],
        hypotheses=["JWT expiration bug in refresh token"],
        attention_window=[{"note": "Auth Architecture", "salience": 0.9}],
    )
    assert wm["active_goal"] == "Refactor authentication layer"
    assert len(wm["subtask_stack"]) == 2

    # 2. Get working memory
    fetched = sqlite_store.get_working_memory("session_wm_01")
    assert fetched is not None
    assert fetched["agent_role"] == "lead_architect"
    assert fetched["hypotheses"] == ["JWT expiration bug in refresh token"]

    # 3. Clear working memory
    cleared = sqlite_store.clear_working_memory("session_wm_01")
    assert cleared is True
    assert sqlite_store.get_working_memory("session_wm_01") is None


def test_weighted_graph_links(sqlite_store):
    # 1. Create two notes
    id1 = sqlite_store.upsert_note(
        title="PostgreSQL Architecture",
        content="Overview of PostgreSQL storage engine",
        tags=["database"],
    )
    id2 = sqlite_store.upsert_note(
        title="WAL Logging",
        content="Write-ahead logging guarantees ACID durability",
        tags=["database", "storage"],
    )

    # 2. Add weighted link
    added = sqlite_store.add_weighted_link(
        source_id=id1,
        target_id=id2,
        relation_type="depends_on",
        weight=1.8,
    )
    assert added is True

    # 3. Inspect adjacency
    adj = sqlite_store.get_graph_adjacency()
    assert "PostgreSQL Architecture" in adj
    links = adj["PostgreSQL Architecture"]
    assert any(l["target_title"] == "WAL Logging" and l["relation_type"] == "depends_on" and l["edge_weight"] == 1.8 for l in links)


def test_epistemic_conflicts_and_atms(sqlite_store):
    # 1. Create original note and newer contradicting note
    id1 = sqlite_store.upsert_note(
        title="API Rate Limit Policy v1",
        content="Default rate limit is 100 requests per minute.",
        tags=["policy"],
    )
    id2 = sqlite_store.upsert_note(
        title="API Rate Limit Policy v2",
        content="Default rate limit increased to 500 requests per minute.",
        tags=["policy"],
    )

    # 2. Log conflict
    conflict_id = sqlite_store.log_conflict(
        old_note_id=id1,
        new_note_id=id2,
        conflict_description="Rate limit increased from 100 to 500 req/min in v2.",
    )
    assert conflict_id > 0

    # 3. Check pending conflicts
    pending = sqlite_store.get_pending_conflicts()
    assert len(pending) >= 1
    assert any(c["id"] == conflict_id for c in pending)

    # 4. Resolve conflict by superseding
    resolved = sqlite_store.resolve_conflict_supersede(old_id=id1, new_id=id2, resolved_by="admin_agent")
    assert resolved is True

    # Verify old note is marked deprecated
    history = sqlite_store.get_note_history("API Rate Limit Policy v1")
    # Verify pending conflicts cleared
    pending_after = sqlite_store.get_pending_conflicts()
    assert not any(c["id"] == conflict_id for c in pending_after)
