"""4.0.4 hardening: no silent split-brain, no open dashboard, no alphabet-seeded REM."""
import os

import pytest

from gomaa.core import UnifiedMemorySystem

BODY = "A body long enough for the admission controller to accept it, with detail."


# --- A: a configured Postgres DSN must not degrade to a private SQLite file ---

def test_unreachable_postgres_raises_instead_of_falling_back(monkeypatch, tmp_path):
    from gomaa.stores import create_store

    monkeypatch.delenv("MEMORY_ALLOW_SQLITE_FALLBACK", raising=False)
    monkeypatch.setenv("MEMORY_SQLITE_PATH", str(tmp_path / "fallback.db"))
    with pytest.raises(RuntimeError, match="split the store"):
        create_store("postgresql://nobody@127.0.0.1:9/nothing?connect_timeout=2")


def test_explicit_opt_in_still_allows_the_fallback(monkeypatch, tmp_path):
    from gomaa.stores import create_store
    from gomaa.stores.sqlite import SQLiteStore

    monkeypatch.setenv("MEMORY_ALLOW_SQLITE_FALLBACK", "1")
    monkeypatch.setenv("MEMORY_SQLITE_PATH", str(tmp_path / "fallback.db"))
    store = create_store("postgresql://nobody@127.0.0.1:9/nothing?connect_timeout=2")
    assert isinstance(store, SQLiteStore)


def test_a_plain_sqlite_path_is_untouched(monkeypatch, tmp_path):
    from gomaa.stores import create_store
    from gomaa.stores.sqlite import SQLiteStore

    monkeypatch.delenv("MEMORY_ALLOW_SQLITE_FALLBACK", raising=False)
    assert isinstance(create_store(str(tmp_path / "x.db")), SQLiteStore)


# --- E: the dashboard may not listen publicly without a token ---

def test_public_bind_without_token_is_refused(monkeypatch):
    from gomaa.dashboard.server import _refuse_open_bind

    monkeypatch.delenv("GOMAA_DASHBOARD_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="without GOMAA_DASHBOARD_TOKEN"):
        _refuse_open_bind("0.0.0.0")
    monkeypatch.setenv("GOMAA_DASHBOARD_TOKEN", "x")
    _refuse_open_bind("0.0.0.0")          # now allowed


def test_loopback_bind_needs_no_token(monkeypatch):
    from gomaa.dashboard.server import _refuse_open_bind

    monkeypatch.delenv("GOMAA_DASHBOARD_TOKEN", raising=False)
    _refuse_open_bind("127.0.0.1")
    _refuse_open_bind("::1")


# --- B: REM discovery must not depend on the letter "a" ---

def test_rem_phase_works_when_keyword_search_is_unavailable(monkeypatch, tmp_path):
    mem = UnifiedMemorySystem(vault_path=str(tmp_path / "v"), dsn=str(tmp_path / "g.db"),
                              auto_sync=False)
    for i, t in enumerate(["Deploy Pipeline", "Deploy Rollback", "Deploy Runbook"]):
        mem.remember(t, BODY + f" {i}", wing="ops", room="rem")

    from gomaa.consolidation import ConsolidationEngine

    engine = ConsolidationEngine(db=mem.db, vault=mem.vault, embedder=mem.embedder)

    def boom(*a, **k):
        raise AssertionError('REM still seeds from search_keyword("a")')

    monkeypatch.setattr(mem.db, "search_keyword", boom)
    stats = engine._phase_rem_associative_synthesis()
    assert isinstance(stats, dict) and "discovered_links" in stats
