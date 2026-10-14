"""
Tests for HippoRAG 2 Associative Retrieval Engine (Gomaa v4.0).
Verifies:
- Personalized PageRank (PPR) power iteration convergence
- Weighted edge transmission
- Single-step multi-hop associative retrieval in SQLiteStore
"""

from gomaa.hipporag import HippoRAGEngine
from gomaa.stores.sqlite import SQLiteStore


def test_hipporag_ppr_power_iteration():
    engine = HippoRAGEngine(restart_prob=0.15, max_iter=25)

    # Graph topology: A -> B -> C
    #                  A -> D (lower weight)
    adjacency = {
        "Node_A": [
            {"target_title": "Node_B", "edge_weight": 2.0, "relation_type": "causes"},
            {"target_title": "Node_D", "edge_weight": 0.5, "relation_type": "associative"},
        ],
        "Node_B": [
            {"target_title": "Node_C", "edge_weight": 1.0, "relation_type": "associative"},
        ],
    }

    # Seed is strictly Node_A
    seed_scores = {"Node_A": 1.0}

    ppr = engine.compute_ppr(adjacency, seed_scores)

    assert "Node_A" in ppr
    assert "Node_B" in ppr
    assert "Node_C" in ppr
    assert "Node_D" in ppr

    # Node_A is restart seed so has highest baseline mass
    assert ppr["Node_A"] > 0.15
    # Node_B received 4x the weight of Node_D from Node_A
    assert ppr["Node_B"] > ppr["Node_D"]
    # Node_C received multi-hop mass via Node_B
    assert ppr["Node_C"] > 0.0


def test_hipporag_store_associative_search(tmp_path):
    db_file = tmp_path / "hipporag_test.db"
    store = SQLiteStore(str(db_file))

    # Create 3 notes:
    # 1. "Docker Daemon" (has query keywords)
    # 2. "Containerd Socket" (linked from Docker, no direct query keywords)
    # 3. "Kubernetes CRI" (linked from Containerd, 2 hops away)
    id1 = store.upsert_note(
        title="Docker Daemon",
        content="Docker daemon manages core container lifecycles.",
        tags=["devops"],
        embedding=[1.0, 0.0, 0.0],
    )
    id2 = store.upsert_note(
        title="Containerd Socket",
        content="Unix domain socket for low-level OCI container runtime.",
        tags=["runtime"],
        embedding=[0.0, 1.0, 0.0],
    )
    id3 = store.upsert_note(
        title="Kubernetes CRI",
        content="Container Runtime Interface plugin for kubelet pods.",
        tags=["k8s"],
        embedding=[0.0, 0.0, 1.0],
    )

    # Add weighted links: Docker Daemon -> Containerd Socket -> Kubernetes CRI
    store.add_weighted_link(id1, id2, relation_type="depends_on", weight=2.0)
    store.add_weighted_link(id2, id3, relation_type="implements", weight=1.5)

    # Search with embedding that matches Docker Daemon [1.0, 0.0, 0.0]
    ppr_results = store.search_associative_ppr(query_embedding=[1.0, 0.0, 0.0], top_k=5)

    assert len(ppr_results) >= 2
    titles = [r["title"] for r in ppr_results]
    assert "Docker Daemon" in titles
    # Crucial HippoRAG validation: Containerd Socket is retrieved via associative graph walk
    assert "Containerd Socket" in titles
    assert ppr_results[0]["ppr_score"] > 0.0

    # Also test hybrid search includes HippoRAG source
    hybrid = store.hybrid_search("Docker Daemon", query_embedding=[1.0, 0.0, 0.0], top_k=5)
    assert len(hybrid) >= 2
    top_sources = [s for r in hybrid for s in r.get("sources", [])]
    assert "hipporag_ppr" in top_sources


def test_hipporag_bidirectional_backlink_ppr(tmp_path):
    db_file = tmp_path / "hipporag_backlink.db"
    store = SQLiteStore(str(db_file))

    # Source_Node links forward to Target_Anchor, but query matches Target_Anchor
    id_src = store.upsert_note(
        title="Root Cause Exploit CVE-2026",
        content="Buffer overflow in legacy parser module.",
        tags=["security"],
        embedding=[0.0, 1.0, 0.0],
    )
    id_tgt = store.upsert_note(
        title="Production WAF Alert",
        content="WAF triggered anomaly on parser endpoint.",
        tags=["security"],
        embedding=[1.0, 0.0, 0.0],
    )
    # Directed link: Root Cause -> Production WAF Alert
    store.add_weighted_link(id_src, id_tgt, relation_type="causes", weight=2.0)

    # Query matches Production WAF Alert ([1.0, 0.0, 0.0]); PPR should traverse backlink to Root Cause
    results = store.search_associative_ppr(query_embedding=[1.0, 0.0, 0.0], top_k=5)
    titles = [r["title"] for r in results]
    assert "Production WAF Alert" in titles
    assert "Root Cause Exploit CVE-2026" in titles
