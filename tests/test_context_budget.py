"""assemble_context must respect max_tokens, not just approximate it."""
import pytest

from gomaa.core import UnifiedMemorySystem

LONG = ("Context budget regression. " * 400)  # ~10.8 kB, far over a 400-char budget


@pytest.fixture
def mem(tmp_path):
    m = UnifiedMemorySystem(vault_path=str(tmp_path / "vault"), dsn=str(tmp_path / "g.db"))
    m.remember("Long note", LONG, wing="operations", room="testing")
    return m


def test_first_hit_is_truncated_not_packed_whole(mem):
    r = mem.assemble_context("context budget", max_tokens=100)
    ctx = r["context_text"]

    # 100 tokens ~ 400 chars; allow a small wrapper overhead, not a 125x overrun.
    assert r["estimated_tokens"] <= 130, f"budget blown: {r['estimated_tokens']} tokens"
    assert r["notes_included"] == 1
    assert "[truncated]" in ctx
    assert ctx.rstrip().endswith("</memory_context>"), "truncation must not break the wrapper"


def test_larger_budget_still_respected(mem):
    r = mem.assemble_context("context budget", max_tokens=400)
    assert r["estimated_tokens"] <= 440
    assert len(r["context_text"]) > 300
