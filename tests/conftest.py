import pytest
import os


@pytest.fixture(scope="session")
def postgres_dsn():
    return os.environ.get("MEMORY_DB_DSN", "postgresql://mnemosyne:***@localhost:5432/mnemosyne")


def pytest_sessionfinish(session, exitstatus):
    """Ensure clean process exit on Darwin/macOS arm64 without OpenMP C++ thread pool destructor collisions."""
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exitstatus)
