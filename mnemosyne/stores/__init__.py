"""Store backends with auto-detection."""

import os
import logging
from typing import Optional

from mnemosyne.stores.base import MemoryStore
from mnemosyne.stores.postgres import PgVectorStore
from mnemosyne.stores.sqlite import SQLiteStore

logger = logging.getLogger("unified-memory")

__all__ = ["MemoryStore", "PgVectorStore", "SQLiteStore", "create_store"]


def create_store(dsn: Optional[str] = None) -> MemoryStore:
    """
    Auto-detect the best available store.

    Priority:
    1. PostgreSQL (if dsn provided or MEMORY_DB_DSN set and connection works)
    2. SQLite (fallback, always works)
    """
    dsn = dsn or os.environ.get("MEMORY_DB_DSN")

    if dsn:
        try:
            store = PgVectorStore(dsn)
            logger.info(f"Using PostgreSQL store: {dsn}")
            return store
        except Exception as e:
            logger.warning(f"PostgreSQL unavailable ({e}), falling back to SQLite")

    sqlite_path = os.environ.get(
        "MEMORY_SQLITE_PATH",
        os.path.expanduser("~/.mnemosyne/mnemosyne.db")
    )
    logger.info(f"Using SQLite store: {sqlite_path}")
    return SQLiteStore(sqlite_path)
