import os
import pytest
from unittest.mock import patch, MagicMock
from gomaa.stores import create_store


class TestCreateStore:
    def test_prefers_postgresql_when_available(self):
        with patch("gomaa.stores.PgVectorStore") as mock_pg:
            mock_pg.return_value = MagicMock()
            create_store("postgresql://localhost/test")
            mock_pg.assert_called_once()

    def test_falls_back_to_sqlite(self, monkeypatch):
        """A configured Postgres DSN that cannot connect must raise, not fall back.

        The silent fallback used to be the default; it turned a database outage into a
        private, invisible copy — every agent kept writing success: true into a file
        nobody else read. It is now opt-in via MEMORY_ALLOW_SQLITE_FALLBACK=1.
        """
        monkeypatch.setenv("MEMORY_REQUIRE_POSTGRES", "false")
        monkeypatch.delenv("MEMORY_ALLOW_SQLITE_FALLBACK", raising=False)
        with patch("gomaa.stores.PgVectorStore") as mock_pg:
            mock_pg.side_effect = Exception("No PG")
            with patch("gomaa.stores.SQLiteStore") as mock_sqlite:
                mock_sqlite.return_value = MagicMock()
                with pytest.raises(RuntimeError, match="split the store"):
                    create_store("postgresql://localhost/test")
                mock_sqlite.assert_not_called()

    def test_the_error_names_the_opt_in_flag(self, monkeypatch):
        """The failure has to be actionable: it must say how to get the old behaviour."""
        monkeypatch.setenv("MEMORY_REQUIRE_POSTGRES", "false")
        monkeypatch.delenv("MEMORY_ALLOW_SQLITE_FALLBACK", raising=False)
        with patch("gomaa.stores.PgVectorStore") as mock_pg:
            mock_pg.side_effect = Exception("No PG")
            with pytest.raises(RuntimeError, match="MEMORY_ALLOW_SQLITE_FALLBACK=1"):
                create_store("postgresql://localhost/test")

    def test_falls_back_to_sqlite_when_explicitly_allowed(self, monkeypatch):
        monkeypatch.setenv("MEMORY_REQUIRE_POSTGRES", "false")
        monkeypatch.setenv("MEMORY_ALLOW_SQLITE_FALLBACK", "1")
        with patch("gomaa.stores.PgVectorStore") as mock_pg:
            mock_pg.side_effect = Exception("No PG")
            with patch("gomaa.stores.SQLiteStore") as mock_sqlite:
                mock_sqlite.return_value = MagicMock()
                create_store("postgresql://localhost/test")
                mock_sqlite.assert_called_once()

    def test_raises_when_postgres_required(self, monkeypatch):
        monkeypatch.setenv("MEMORY_REQUIRE_POSTGRES", "true")
        monkeypatch.delenv("MEMORY_ALLOW_SQLITE_FALLBACK", raising=False)
        with patch("gomaa.stores.PgVectorStore") as mock_pg:
            mock_pg.side_effect = Exception("No PG")
            with pytest.raises(RuntimeError, match="PostgreSQL required"):
                create_store("postgresql://localhost/test")
