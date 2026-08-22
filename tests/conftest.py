import pytest
import os


@pytest.fixture(scope="session")
def postgres_dsn():
    return os.environ.get(
        "MEMORY_DB_DSN", "postgresql://mnemosyne:mnemosyne@localhost:5432/mnemosyne"
    )
