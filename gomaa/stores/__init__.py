"""Store backends with auto-detection."""

import os
import logging
from typing import Optional

from gomaa.stores.base import MemoryStore
from gomaa.stores.postgres import PgVectorStore
from gomaa.stores.sqlite import SQLiteStore

logger = logging.getLogger("unified-memory")

__all__ = ["MemoryStore", "PgVectorStore", "SQLiteStore", "create_store"]


def create_store(dsn: Optional[str] = None) -> MemoryStore:
    """
    Auto-detect the best available store.

    Priority:
    1. Direct SQLite file path or sqlite:// URI
    2. PostgreSQL (if dsn provided or MEMORY_DB_DSN set and connection works)
    3. SQLite (fallback, always works — unless MEMORY_REQUIRE_POSTGRES=true)
    """
    dsn = dsn or os.environ.get("MEMORY_DB_DSN")
    require_pg = os.environ.get("MEMORY_REQUIRE_POSTGRES", "").lower() in ("true", "1", "yes")

    if dsn:
        # Check if explicitly an SQLite path
        if dsn.startswith("sqlite://"):
            return SQLiteStore(db_path=dsn.replace("sqlite://", ""))
        if (
            dsn.endswith(".db")
            or dsn.endswith(".sqlite")
            or "/" in dsn
            and not (
                dsn.startswith("postgresql://") or dsn.startswith("postgres://") or "dbname=" in dsn or "host=" in dsn
            )
        ):
            return SQLiteStore(db_path=dsn)

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

    sqlite_path = os.environ.get("MEMORY_SQLITE_PATH", os.path.expanduser("~/.gomaa/gomaa.db"))
    logger.info(f"Using SQLite store: {sqlite_path}")
    return SQLiteStore(sqlite_path)
