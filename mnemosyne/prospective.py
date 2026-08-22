"""Prospective memory (scheduled reminders)."""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger("unified-memory")


class ProspectiveMemory:
    """Remember to do something in the future."""

    def __init__(self, db):
        self.db = db

    def schedule(
        self, title: str, content: str, trigger_at: str, recurring: Optional[str] = None
    ) -> str:
        """Schedule a future reminder. trigger_at: ISO 8601 datetime string."""
        with self.db._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO prospective (title, content, trigger_at, recurring)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                """,
                    (title, content, trigger_at, recurring),
                )
                pid = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Scheduled reminder: {title} at {trigger_at}")
                return pid

    def get_due(self, window_hours: int = 24) -> List[Dict]:
        """Get reminders due within the next N hours."""
        with self.db._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, content, trigger_at, recurring
                    FROM prospective
                    WHERE status = 'pending'
                      AND trigger_at <= NOW() + INTERVAL '%s hours'
                    ORDER BY trigger_at;
                """,
                    (window_hours,),
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def mark_done(self, reminder_id: str):
        """Mark a reminder as completed."""
        with self.db._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE prospective SET status = 'done' WHERE id = %s;", (reminder_id,))
                conn.commit()
