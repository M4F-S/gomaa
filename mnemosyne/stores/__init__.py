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
    2. SQLite (fallback, always works — unless MEMORY_REQUIRE_POSTGRES=true)

    Set MEMORY_REQUIRE_POSTGRES=true to raise an error instead of silently
    falling back to SQLite when PostgreSQL is unreachable.
    """
    dsn = dsn or os.environ.get("MEMORY_DB_DSN")
    require_pg = os.environ.get("MEMORY_REQUIRE_POSTGRES", "").lower() in ("true", "1", "yes")

    if dsn:
        try:
            store = PgVectorStore(dsn)
            logger.info(f"Using PostgreSQL store: {dsn}")
            return store
        except Exception as e:
            if require_pg:
                raise RuntimeError(
                    f"PostgreSQL required (MEMORY_REQUIRE_POSTGRES=true) but connection failed: {e}"
                ) from e
            logger.warning(
                f"⚠️ FALLBACK: PostgreSQL unavailable ({e}). "
                f"Using local SQLite instead. Set MEMORY_REQUIRE_POSTGRES=true to prevent this."
            )

    sqlite_path = os.environ.get(
        "MEMORY_SQLITE_PATH",
        os.path.expanduser("~/.mnemosyne/mnemosyne.db")
    )
    logger.info(f"Using SQLite store: {sqlite_path}")
    return SQLiteStore(sqlite_path)
