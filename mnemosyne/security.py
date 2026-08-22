"""Admission control and salience scoring."""

import re
import logging
from typing import Dict, Tuple, Optional, Any

logger = logging.getLogger("unified-memory")


class AdmissionControl:
    """
    Validates memory writes before they become persistent.
    Protects against poisoning, contradictions, and low-quality data.
    """

    def __init__(self, db=None, embedder=None):
        self.db = db
        self.embedder = embedder

    def validate(self, title: str, content: str, tags: Optional[Any] = None) -> Tuple[bool, str]:
        """
        Validate a proposed memory write.
        Returns: (is_valid, reason)
        """
        checks = []

        # Length gate
        if len(content) < 10:
            checks.append((False, "Content too short (< 10 chars)"))
        if len(content) > 50000:
            checks.append((False, "Content too long (> 50000 chars)"))

        # Injection pattern detection
        injection_patterns = [
            r"ignore previous instructions",
            r"disregard (all|your) (instructions|training)",
            r"system prompt",
            r"you are now",
            r"DAN mode",
        ]
        content_lower = content.lower()
        for pattern in injection_patterns:
            if re.search(pattern, content_lower):
                checks.append((False, f"Potential injection pattern detected: {pattern}"))

        # Near-duplicate detection
        if self.db is not None and self.embedder is not None:
            try:
                emb = self.embedder.embed([content])[0]
                similar = self.db.search_semantic(emb, top_k=5)
                for s in similar:
                    if s.get("score", 0) > 0.92:
                        checks.append((True, f"Near-duplicate of existing note: {s['title']}"))
            except Exception:
                pass

        # Contradiction check
        if self.db is not None:
            try:
                existing = self.db.search_keyword(title, top_k=1)
                if existing and existing[0]["title"].lower() == title.lower():
                    checks.append((True, "Title exists — will update rather than create new"))
            except Exception:
                pass

        if any(not c[0] for c in checks):
            reason = "; ".join(c[1] for c in checks if not c[0])
            return False, reason

        reason = "; ".join(c[1] for c in checks) if checks else "All checks passed"
        return True, reason


class SalienceEngine:
    """
    Scores memory importance so important things persist longer.
    """

    @staticmethod
    def score(frontmatter: Dict, content: str, db_stats: Dict) -> float:
        """Calculate salience score (0.0 to 1.0)."""
        score = 0.5
        emphasis_markers = ["IMPORTANT", "CRITICAL", "DECISION", "ALERT", "WARNING"]
        content_upper = content.upper()
        for marker in emphasis_markers:
            if marker in content_upper:
                score += 0.15
        type_weights = {"decision": 0.2, "security": 0.25, "MOC": 0.1, "journal": -0.1}
        score += type_weights.get(frontmatter.get("type", ""), 0.0)
        if len(content) > 500:
            score += 0.05
        if "salience" in frontmatter:
            score = (score + float(frontmatter["salience"])) / 2
        return max(0.0, min(1.0, score))
