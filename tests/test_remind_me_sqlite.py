"""Regression: remind_me must not report success when scheduling actually failed.

Production runs PG (full-featured). Default/no-DSN path uses SQLite. Prior behavior
swallowed backend SQL errors in core.remind_me and returned success:True anyway,
which would mislead an agent into believing a reminder was scheduled.
"""
import sys

import pytest

from gomaa import UnifiedMemorySystem


@pytest.fixture
def sqlite_mem(tmp_path, monkeypatch):
    # Force the SQLite path deterministically (env may otherwise select Postgres).
    monkeypatch.delenv("MEMORY_DB_DSN", raising=False)
    monkeypatch.delenv("MEMORY_SHARED_DSN", raising=False)
    mem = UnifiedMemorySystem(
        vault_path=str(tmp_path),
        dsn=f"sqlite:///{tmp_path}/mem.db",
        auto_sync=False,
    )
    return mem


def test_remind_me_works_on_sqlite(sqlite_mem):
    """On a backend with a working prospective table, scheduling should succeed."""
    res = sqlite_mem.remind_me(
        "pay bills", "remember to pay rent", "2099-01-01T09:00:00"
    )
    assert res.get("success") is True
    assert res.get("reminder_id") is not None


def test_remind_me_no_false_success_when_schedule_fails(monkeypatch, sqlite_mem):
    """If the prospective store genuinely can't schedule, success must be False."""
    # Force a backend-level failure inside schedule.
    def boom(*a, **k):
        raise ValueError("backend cannot schedule")

    monkeypatch.setattr(sqlite_mem.prospective, "schedule", boom)
    res = sqlite_mem.remind_me(
        title="do thing", content="do it soon", trigger_at="2099-01-01T00:00:00"
    )
    assert res.get("success") is False
    assert res.get("reminder_id") is None


def test_get_due_returns_same_day_trigger(sqlite_mem):
    """A trigger a few minutes in the past (same day, ISO 'T' separator) must be
    due. Regression for the T-vs-space string-compare bug in get_due_reminders."""
    from datetime import datetime, timedelta, timezone

    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
    rid = sqlite_mem.prospective.schedule("task-now", "do it now", past)
    due = sqlite_mem.prospective.get_due(window_hours=1)
    assert any(d["id"] == rid for d in due), "past/now trigger not returned as due"


def test_get_due_excludes_future(sqlite_mem):
    """A future trigger must not be returned as due."""
    future = "2099-01-01T00:00:00"
    rid = sqlite_mem.prospective.schedule("future-task", "later", future)
    due = sqlite_mem.prospective.get_due(window_hours=24)
    assert not any(d["id"] == rid for d in due)