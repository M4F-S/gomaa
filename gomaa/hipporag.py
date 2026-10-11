"""
HippoRAG 2 Associative Memory Walker for Gomaa (v4.0).
Implements Hippocampal Indexing Theory via Personalized PageRank (PPR).
Enables single-step multi-hop retrieval across associative knowledge graphs.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("gomaa-hipporag")


class HippoRAGEngine:
    """
    Hippocampal Indexing Engine using Personalized PageRank (PPR).
    Replaces static BFS multi-hop traversals with dynamic probability diffusion.
    """

    def __init__(self, restart_prob: float = 0.15, max_iter: int = 20, tol: float = 1e-5):
        self.alpha = restart_prob
        self.max_iter = max_iter
        self.tol = tol

    def compute_ppr(
        self,
        adjacency: Dict[str, List[Dict[str, Any]]],
        seed_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute Personalized PageRank stationary distribution over graph adjacency.

        :param adjacency: {source_title: [{"target_title": str, "edge_weight": float, "relation_type": str}]}
        :param seed_scores: {node_title: initial_similarity_weight}
        :return: {node_title: ppr_score}
        """
        if not seed_scores:
            return {}

        # 1. Collect all unique nodes in graph and seeds
        all_nodes = set(seed_scores.keys())
        for src, targets in adjacency.items():
            all_nodes.add(src)
            for tgt in targets:
                all_nodes.add(tgt["target_title"])

        node_list = sorted(list(all_nodes))
        node_to_idx = {name: i for i, name in enumerate(node_list)}
        N = len(node_list)
        if N == 0:
            return {}

        # 2. Build seed vector p0 (normalized)
        p0 = [0.0] * N
        total_seed = sum(max(0.0, s) for s in seed_scores.values())
        if total_seed > 0:
            for name, score in seed_scores.items():
                if name in node_to_idx:
                    p0[node_to_idx[name]] = max(0.0, score) / total_seed
        else:
            p0 = [1.0 / N] * N

        # 3. Build row-stochastic transition weights
        transitions: Dict[int, List[Tuple[int, float]]] = {}
        for src, targets in adjacency.items():
            if src not in node_to_idx:
                continue
            src_idx = node_to_idx[src]
            valid_targets = [t for t in targets if t.get("target_title") in node_to_idx]
            total_weight = sum(max(0.01, float(t.get("edge_weight", 1.0))) for t in valid_targets)
            if total_weight > 0:
                transitions[src_idx] = [
                    (node_to_idx[t["target_title"]], max(0.01, float(t.get("edge_weight", 1.0))) / total_weight)
                    for t in valid_targets
                ]

        # 4. Power iteration: p_{k+1} = (1 - alpha) * W^T * p_k + alpha * p0
        p = list(p0)
        for _ in range(self.max_iter):
            next_p = [self.alpha * p0[i] for i in range(N)]

            # Scatter probability mass along outgoing edges
            for src_idx in range(N):
                src_mass = p[src_idx]
                if src_idx in transitions and transitions[src_idx]:
                    for tgt_idx, prob in transitions[src_idx]:
                        next_p[tgt_idx] += (1.0 - self.alpha) * src_mass * prob
                else:
                    # Dangling node (out-degree 0): distribute back according to seed vector
                    for i in range(N):
                        next_p[i] += (1.0 - self.alpha) * src_mass * p0[i]

            # Check convergence L1 norm
            diff = sum(abs(next_p[i] - p[i]) for i in range(N))
            p = next_p
            if diff < self.tol:
                break

        return {node_list[i]: p[i] for i in range(N)}
