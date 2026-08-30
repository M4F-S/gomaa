"""Prospective memory (scheduled reminders)."""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger("unified-memory")


class ProspectiveMemory:
    """Remember to do something in the future."""

    def __init__(self, db):
        self.db = db

    def schedule(self, title: str, content: str, trigger_at: str, recurring: Optional[str] = None) -> str:
        """Schedule a future reminder. trigger_at: ISO 8601 datetime string."""
        rid = self.db.schedule_reminder(title, content, trigger_at, recurring)
        logger.info(f"Scheduled reminder: {title} at {trigger_at}")
        return rid

    def get_due(self, window_hours: int = 24) -> List[Dict]:
        """Get reminders due within the next N hours."""
        return self.db.get_due_reminders(window_hours=window_hours)

    def mark_done(self, reminder_id: str):
        """Mark a reminder as completed."""
        self.db.mark_reminder_done(reminder_id)
