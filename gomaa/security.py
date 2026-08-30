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

        # Injection pattern detection (evaluated across all content to prevent backtick/code fence evasion)
        content_lower = content.lower()

        injection_patterns = [
            r"ignore\s+(all\s+)?(previous\s+|prior\s+|your\s+)?(instructions|commands|directives|rules|system\s+prompt)",
            r"disregard\s+(all\s+)?(previous\s+|prior\s+|your\s+)?(instructions|training|system\s+prompt|rules|commands|directives)",
            r"you\s+must\s+ignore\s+(the\s+)?system\s+prompt",
            r"you\s+are\s+now\s+(in\s+)?(unrestricted|dan|jailbreak)\s+mode",
            r"\bdan\s+mode\b",
            r"\bjailbreak\s+mode\b",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, content_lower):
                checks.append((False, f"Potential injection pattern detected: {pattern}"))

        # Near-duplicate detection
        if self.db is not None and self.embedder is not None:
            try:
                if hasattr(self.embedder, "embed_query"):
                    emb = self.embedder.embed_query(content)
                elif hasattr(self.embedder, "embed"):
                    emb = self.embedder.embed([content])[0]
                else:
                    emb = []
                if emb:
                    similar = self.db.search_semantic(emb, top_k=5)
                    for s in similar:
                        if s.get("score", 0) > 0.92:
                            checks.append((True, f"Near-duplicate of existing note: {s['title']}"))
            except Exception as e:
                logger.warning(f"AdmissionControl near-duplicate check bypassed due to error: {e}")

        # Contradiction check
        if self.db is not None:
            try:
                existing = self.db.search_keyword(title, top_k=1)
                if existing and existing[0]["title"].lower() == title.lower():
                    checks.append((True, "Title exists — will update rather than create new"))
            except Exception as e:
                logger.warning(f"AdmissionControl contradiction check bypassed due to error: {e}")

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
