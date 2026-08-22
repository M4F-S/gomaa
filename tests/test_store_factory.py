import pytest
from unittest.mock import patch, MagicMock
from mnemosyne.stores import create_store


class TestCreateStore:
    def test_prefers_postgresql_when_available(self):
        with patch("mnemosyne.stores.PgVectorStore") as mock_pg:
            mock_pg.return_value = MagicMock()
            create_store("postgresql://localhost/test")
            mock_pg.assert_called_once()

    def test_falls_back_to_sqlite(self):
        with patch("mnemosyne.stores.PgVectorStore") as mock_pg:
            mock_pg.side_effect = Exception("No PG")
            with patch("mnemosyne.stores.SQLiteStore") as mock_sqlite:
                mock_sqlite.return_value = MagicMock()
                create_store("postgresql://localhost/test")
                mock_sqlite.assert_called_once()
