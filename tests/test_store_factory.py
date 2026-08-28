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

    def test_falls_back_to_sqlite(self):
        with patch.dict(os.environ, {"MEMORY_REQUIRE_POSTGRES": "false"}):
            with patch("gomaa.stores.PgVectorStore") as mock_pg:
                mock_pg.side_effect = Exception("No PG")
                with patch("gomaa.stores.SQLiteStore") as mock_sqlite:
                    mock_sqlite.return_value = MagicMock()
                    create_store("postgresql://localhost/test")
                    mock_sqlite.assert_called_once()

    def test_raises_when_postgres_required(self):
        with patch.dict(os.environ, {"MEMORY_REQUIRE_POSTGRES": "true"}):
            with patch("gomaa.stores.PgVectorStore") as mock_pg:
                mock_pg.side_effect = Exception("No PG")
                with pytest.raises(RuntimeError, match="PostgreSQL required"):
                    create_store("postgresql://localhost/test")
