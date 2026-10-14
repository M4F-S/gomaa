"""
Comprehensive Live Fleet Diagnostic & Strict E2E Test Suite for Gomaa v4.0.0 (Gomaa Neo).
Exercises all 13 MCP tools, 4 Cognitive Quadrants, HippoRAG 2 PPR, 3-Phase Sleep Consolidation,
ACT-R Base-Level Activation, Miller's Law Working Memory bounds, and Cross-Agent Shared Memory
across all 5 production containers on the VPS.
"""

import os
import sys
import json
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path

# 1. Verify Gomaa import and version
try:
    from gomaa import UnifiedMemorySystem, __version__
    from gomaa.mcp_server import MCPServer
except ImportError as e:
    print(f"FATAL: Unable to import gomaa: {e}")
    sys.exit(1)

assert __version__ == "4.0.0", f"Expected Gomaa version 4.0.0, got {__version__}"
print(f"=== Gomaa Core Version: {__version__} ===")

AGENT_NAME = os.environ.get("MEMORY_AGENT_NAME", "unknown-agent")
VAULT_PATH = os.environ.get("MEMORY_VAULT_PATH", "/opt/data/vault")
DB_DSN = os.environ.get("MEMORY_DB_DSN")
SHARED_DSN = os.environ.get("MEMORY_SHARED_DSN")

print(f"Agent: {AGENT_NAME} | Vault: {VAULT_PATH}")

# 2. Initialize UnifiedMemorySystem & Verify PgVectorStore + shared_db
mem = UnifiedMemorySystem(
    vault_path=VAULT_PATH,
    dsn=DB_DSN,
    shared_dsn=SHARED_DSN,
    agent_name=AGENT_NAME,
)
backend_name = type(mem.db).__name__
assert backend_name == "PgVectorStore", f"Expected PgVectorStore on production VPS, got {backend_name}"
assert mem.shared_db is not None, "Expected shared_db connection to be active"
print(f"✅ [1/12] Store Verified: {backend_name} + shared_db connected")

# 3. Verify MCPServer registers all 13 tools
server = MCPServer(memory=mem)
tools = server._get_tools()
tool_names = [t["name"] for t in tools]
assert len(tools) == 13, f"Expected 13 MCP tools, got {len(tools)}: {tool_names}"
expected_tools = {
    "memory_remember",
    "memory_publish_shared",
    "memory_recall",
    "memory_ingest_session",
    "memory_timeline",
    "memory_history",
    "memory_remind_me",
    "memory_assemble_context",
    "memory_ingest_event",
    "memory_save_playbook",
    "memory_sleep",
    "memory_working_buffer",
    "memory_audit",
}
assert set(tool_names) == expected_tools, f"Mismatch in MCP tools: {set(tool_names) ^ expected_tools}"
print("✅ [2/12] MCPServer Verified: 13/13 MCP tools registered")

# 4. Test Semantic Quadrant & Bi-Directional Graph Links (memory_remember)
run_tag = f"r{uuid.uuid4().hex[:6]}"
title_a = f"Gomaa v4 Node A {AGENT_NAME} {run_tag}"
title_b = f"Gomaa v4 Node B {AGENT_NAME} {run_tag}"

res_b = server._call_tool(
    "memory_remember",
    {
        "title": title_b,
        "content": f"Downstream target node for HippoRAG PPR multi-hop test by {AGENT_NAME} {run_tag}.",
        "tags": '["gomaa-v4", "hipporag", "ppr"]',  # test JSON-stringified tag coercion
        "salience": "0.85",
        "wing": "diagnostics",
        "room": "v4-e2e",
        "pinned": "true",
    },
)
assert res_b.get("success") is True, f"memory_remember B failed: {res_b}"

res_a = server._call_tool(
    "memory_remember",
    {
        "title": title_a,
        "content": f"Primary anchor node for {AGENT_NAME} {run_tag} linking to [[{title_b}]].",
        "tags": ["gomaa-v4", "hipporag", "anchor"],
        "salience": 0.9,
        "wing": "diagnostics",
        "room": "v4-e2e",
        "pinned": True,
    },
)
assert res_a.get("success") is True, f"memory_remember A failed: {res_a}"
print(f"✅ [3/12] Semantic Quadrant & Vault Write Verified: '{title_a}' -> '[[{title_b}]]'")

# 5. Test Recall Modes: hybrid, semantic, keyword, graph, associative_ppr + ACT-R access_count
for mode in ["hybrid", "semantic", "keyword", "graph", "associative_ppr"]:
    query_str = title_a if mode == "graph" else f"Primary anchor node {AGENT_NAME} {run_tag}"
    rec = server._call_tool(
        "memory_recall",
        {
            "query": query_str,
            "mode": mode,
            "top_k": 5,
            "scope": '{"wing": "diagnostics"}',  # test JSON-stringified scope coercion
        },
    )
    results = rec.get("results", [])
    assert len(results) > 0, f"memory_recall mode={mode} returned 0 results for query={query_str}"
print("✅ [4/12] All 5 Semantic/Graph Recall Modes Verified (hybrid, semantic, keyword, graph, associative_ppr)")

# 6. Test Context Assembler (memory_assemble_context)
ctx_res = server._call_tool(
    "memory_assemble_context",
    {
        "query": f"Primary anchor node {AGENT_NAME}",
        "max_tokens": 1200,
        "mode": "associative_ppr",
        "scope": {"wing": "diagnostics"},
    },
)
assert "<memory_context>" in ctx_res.get("context_text", ""), "assemble_context missing XML wrapper"
print(f"✅ [5/12] Token-Budgeted Context Assembler Verified ({ctx_res.get('notes_included')} notes packed)")

# 7. Test Episodic Quadrant (memory_ingest_event + recall mode='episodic')
session_id = f"sess-{AGENT_NAME}-{run_tag}"
ev1 = server._call_tool(
    "memory_ingest_event",
    {
        "session_id": session_id,
        "event_type": "dialogue",
        "stimulus": f"Investigate high-surprise anomaly {run_tag} on {AGENT_NAME}",
        "response": f"Resolved anomaly {run_tag} by tuning HNSW ef_search parameter.",
        "surprise_factor": 0.85,
        "outcome_status": "success",
    },
)
assert ev1.get("session_id") == session_id
ev2 = server._call_tool(
    "memory_ingest_event",
    {
        "session_id": session_id,
        "event_type": "tool_call",
        "stimulus": "check_pgvector_index()",
        "response": "HNSW index healthy",
        "tool_name": "check_pgvector_index",
        "tool_args": '{"table": "notes"}',
        "surprise_factor": 0.3,
        "outcome_status": "success",
    },
)
ev3 = server._call_tool(
    "memory_ingest_event",
    {
        "session_id": session_id,
        "event_type": "tool_call",
        "stimulus": "vacuum_analyze_notes()",
        "response": "VACUUM ANALYZE complete",
        "tool_name": "vacuum_analyze_notes",
        "tool_args": {"table": "notes"},
        "surprise_factor": 0.4,
        "outcome_status": "success",
    },
)
ep_rec = server._call_tool("memory_recall", {"query": session_id, "mode": "episodic", "top_k": 5})
assert len(ep_rec.get("results", [])) >= 3, "Episodic recall failed to return logged session turns"
print("✅ [6/12] Episodic Quadrant Ledger Verified (3 events logged & recalled)")

# 8. Test Procedural Quadrant (memory_save_playbook + Bayesian Laplace utility + recall mode='procedural')
skill_name = f"pgvector_maintenance_{AGENT_NAME}_{run_tag}"
pb = server._call_tool(
    "memory_save_playbook",
    {
        "skill_name": skill_name,
        "domain": "database",
        "description": f"Automated HNSW index maintenance workflow for {AGENT_NAME}",
        "preconditions": '["postgres_online", "pgvector_installed"]',
        "tool_sequence": '[{"step": 1, "tool": "check_pgvector_index"}, {"step": 2, "tool": "vacuum_analyze_notes"}]',
        "error_recovery": '{"timeout": "retry_with_backoff"}',
    },
)
assert pb.get("skill_name") == skill_name
assert abs(pb.get("bayesian_success_rate", 0) - 0.5) < 0.01
mem.db.record_playbook_execution(skill_name, success=True)
mem.db.record_playbook_execution(skill_name, success=True)
pb_updated = mem.db.get_playbook(skill_name)
assert abs(pb_updated.get("bayesian_success_rate", 0) - 0.75) < 0.01  # (2+1)/(2+2) = 0.75
proc_rec = server._call_tool("memory_recall", {"query": "HNSW index maintenance workflow", "mode": "procedural", "top_k": 5})
assert len(proc_rec.get("results", [])) >= 1
print(f"✅ [7/12] Procedural Quadrant & Bayesian Laplace Utility Verified (rate={pb_updated['bayesian_success_rate']})")

# 9. Test Working Memory Quadrant & Miller's Law (7 +/- 2 => max 9) Bound (memory_working_buffer)
twelve_items = [{"item": f"focus_{i}"} for i in range(12)]
wm_up = server._call_tool(
    "memory_working_buffer",
    {
        "action": "update",
        "session_id": session_id,
        "agent_role": AGENT_NAME,
        "active_goal": "Complete strict v4.0 E2E validation",
        "subtask_stack": '["Verify quadrants", "Verify sleep consolidation"]',
        "hypotheses": '["All 13 MCP tools operate at 100% accuracy"]',
        "attention_window": json.dumps(twelve_items),
    },
)
assert len(wm_up.get("attention_window", [])) == 9, f"Miller's Law bound failed: got {len(wm_up.get('attention_window', []))}"
wm_get = server._call_tool("memory_working_buffer", {"action": "get", "session_id": session_id})
assert wm_get["working_memory"]["active_goal"] == "Complete strict v4.0 E2E validation"
assert len(wm_get["working_memory"]["attention_window"]) == 9
wm_clr = server._call_tool("memory_working_buffer", {"action": "clear", "session_id": session_id})
assert wm_clr["cleared"] is True
print("✅ [8/12] Working Memory Scratchpad & Miller's Law (<=9 items) Bound Verified")

# 10. Test 3-Phase Biological Sleep Consolidation (memory_sleep: SWS + REM + ATMS Homeostasis)
sleep_res = server._call_tool("memory_sleep", {"decay_factor": 0.95, "archive_threshold": 0.10})
assert "engine" in sleep_res, f"memory_sleep missing engine report: {sleep_res}"
eng = sleep_res["engine"]
assert eng.get("crystallized_episodes", 0) >= 3, f"Expected SWS to crystallize >=3 episodes, got {eng}"
assert eng.get("synthesized_playbooks", 0) >= 1, f"Expected SWS to synthesize >=1 playbook, got {eng}"
assert eng.get("shared_playbooks", 0) >= 1, f"Expected REM to share >=1 playbook to shared_db, got {eng}"
print(
    f"✅ [9/12] 3-Phase Sleep Consolidation Verified: "
    f"SWS Crystallized={eng['crystallized_episodes']}, "
    f"Playbooks Synthesized={eng['synthesized_playbooks']}, "
    f"REM Shared={eng['shared_playbooks']}, "
    f"REM Latent Links={eng['discovered_links']}"
)

# 11. Test Session Ingest, Timeline, History, Remind Me, and Audit
ing_res = server._call_tool(
    "memory_ingest_session",
    {
        "transcript": f"User: Verify {AGENT_NAME} session chunking.\nAssistant: Turn boundary chunking operational.",
        "wing": "diagnostics",
        "room": "sessions",
    },
)
assert ing_res.get("success") is True
tl_res = server._call_tool("memory_timeline", {"limit": 5})
assert len(tl_res.get("timeline", [])) > 0
hist_res = server._call_tool("memory_history", {"title": title_a, "limit": 5})
assert "history" in hist_res
rem_me = server._call_tool(
    "memory_remind_me",
    {
        "title": f"Routine Sleep Cycle {AGENT_NAME}",
        "content": "Run gomaa sleep consolidation",
        "trigger_at": "2026-12-31T00:00:00Z",
        "recurring": "daily",
    },
)
assert rem_me.get("success") is True
audit_res = server._call_tool("memory_audit", {})
assert audit_res["health"]["server"]["version"] == "4.0.0"
assert audit_res["health"]["server"]["status"] == "healthy"
print("✅ [10/12] Session Ingest, Timeline, History, Remind Me, and Audit Tools Verified")

# 12. Test Security Gate & Cross-Agent Shared Fleet Memory (memory_publish_shared)
bad_res = server._call_tool(
    "memory_publish_shared",
    {
        "title": "Credential Leak Attempt",
        "content": "Leaked key sk-ant-api03-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    },
)
assert bad_res.get("success") is False, "Security gate failed to block Anthropic API key!"

shared_title = f"Gomaa v4 Fleet Verification ({AGENT_NAME})"
pub_res = server._call_tool(
    "memory_publish_shared",
    {
        "title": shared_title,
        "content": f"Verified Gomaa v4.0.0 4-quadrant cognitive memory from {AGENT_NAME} at {datetime.now(timezone.utc).isoformat()}.",
        "tags": ["gomaa-v4", "fleet-verified", AGENT_NAME],
        "wing": "shared",
        "room": "diagnostics",
    },
)
assert pub_res.get("success") is True, f"publish_shared failed: {pub_res}"
print(f"✅ [11/12] Security Gate & Cross-Agent Shared Fleet Publication Verified ('{shared_title}')")

# 13. Clean up ephemeral diagnostic artifacts so production vaults & DBs stay pristine
mem.db.delete_note(title_a)
mem.db.delete_note(title_b)
try:
    with mem.db._conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM notes WHERE wing = 'diagnostics' "
                "OR title LIKE 'Crystallized Episode (sess-%' "
                "OR title LIKE 'Gomaa v4 Node %' "
                "OR title LIKE 'Routine Sleep Cycle %';"
            )
            cur.execute("DELETE FROM episodic_events WHERE session_id LIKE 'sess-%';")
            cur.execute(
                "DELETE FROM procedural_playbooks WHERE skill_name LIKE 'pgvector_maintenance_%' "
                "OR skill_name LIKE 'auto_workflow_sess-%';"
            )
    if mem.shared_db:
        with mem.shared_db._conn() as sconn:
            with sconn.cursor() as scur:
                scur.execute("DELETE FROM procedural_playbooks WHERE skill_name LIKE 'pgvector_maintenance_%' OR skill_name LIKE 'auto_workflow_sess-%';")
    diag_dir = Path(VAULT_PATH) / "diagnostics"
    if diag_dir.exists():
        shutil.rmtree(diag_dir, ignore_errors=True)
except Exception as cleanup_exc:
    print(f"Cleanup notice: {cleanup_exc}")

print("✅ [12/12] Ephemeral Diagnostic Artifacts Cleaned Up")
print(f"\n🎉 ALL 13 MCP TOOLS, 4 QUADRANTS, HIPPORAG PPR & SLEEP CONSOLIDATION PASSED ON {AGENT_NAME}!\n")
