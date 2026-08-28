"""Consolidation engine (sleep-time maintenance)."""

import logging
from typing import Dict

logger = logging.getLogger("unified-memory")


class ConsolidationEngine:
    """
    Nightly batch maintenance:
    - Merge near-duplicate notes
    - Archive stale, low-salience notes
    - Prune orphaned notes
    - Rebuild graph edges
    """

    def __init__(self, db, vault, embedder):
        self.db = db
        self.vault = vault
        self.embedder = embedder

    def run(self, decay_factor: float = 0.95, archive_threshold: float = 0.10) -> Dict:
        """Run full consolidation. Returns stats.

        decay_factor and archive_threshold are accepted for interface parity
        with store-level consolidation; archiving uses archive_threshold.
        """
        stats = {"archived": 0, "relinked": 0}
        stats["archived"] = self._archive_stale(archive_threshold)
        stats["relinked"] = self._rebuild_links()
        logger.info(f"Consolidation complete: {stats}")
        return stats

    def _archive_stale(self, archive_threshold: float = 0.10) -> int:
        """Archive notes not updated in 90 days with salience below threshold."""
        if hasattr(self.db, "archive_stale"):
            return self.db.archive_stale(archive_threshold=archive_threshold, days=90)
        return 0

    def _rebuild_links(self) -> int:
        """Rebuild graph edges from vault notes via store-native reconciliation."""
        if hasattr(self.db, "reconcile_links"):
            return self.db.reconcile_links()
        return 0