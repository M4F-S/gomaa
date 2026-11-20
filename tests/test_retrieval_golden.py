"""A first golden set for retrieval — small, but real queries with known answers.

Not a benchmark. It exists so that a ranking change has to prove it did not make
obvious queries worse; the fixture-based "benchmarks" quoted in the decks could
not do that.
"""
import pytest

from gomaa.core import UnifiedMemorySystem

CORPUS = {
    "Caddy Reverse Proxy": "Caddy serves the subdomains and terminates TLS. Upstreams "
                           "are declared in the Caddyfile and must use the container name.",
    "Postgres Backup Routine": "The nightly pg_dump runs at 03:00 and keeps seven "
                               "snapshots. Restores are rehearsed monthly on a scratch database.",
    "Kernel MPTCP Mitigation": "MPTCP is disabled persistently through a sysctl drop-in to "
                               "close the use-after-free window until Ubuntu ships a patched kernel.",
    "Pharmacy Dispensing Rules": "Austauschregeln and Zuzahlung are checked before handover; "
                                 "the substitution list is updated quarterly.",
    "Telegram Bot Delivery": "Outbound messages use the chat id from the last inbound update, "
                             "because private chat ids are not discoverable by username.",
}

LEXICAL = [
    ("how are upstreams declared in the Caddyfile", "Caddy Reverse Proxy"),
    ("when does the nightly pg_dump run", "Postgres Backup Routine"),
    ("which sysctl closes the MPTCP window", "Kernel MPTCP Mitigation"),
    ("Zuzahlung and Austauschregeln before handover", "Pharmacy Dispensing Rules"),
    ("why use the chat id from the last inbound update", "Telegram Bot Delivery"),
]

PARAPHRASE = [
    ("how do I stop the reverse proxy losing its backend after a restart", "Caddy Reverse Proxy"),
    ("what protects the database if the machine dies", "Postgres Backup Routine"),
]


@pytest.fixture(scope="module")
def mem(tmp_path_factory):
    d = tmp_path_factory.mktemp("golden")
    m = UnifiedMemorySystem(vault_path=str(d / "vault"), dsn=str(d / "g.db"), auto_sync=False)
    for title, body in CORPUS.items():
        m.remember(title, body, wing="qa", room="golden")
    return m


@pytest.mark.parametrize("query,expected", LEXICAL)
def test_lexical_queries_hit_top3(mem, query, expected):
    titles = [r["title"] for r in mem.recall(query, top_k=3)]
    assert expected in titles, f"{expected!r} missing from top-3: {titles}"


@pytest.mark.parametrize("query,expected", PARAPHRASE)
def test_paraphrase_queries_hit_top5(mem, query, expected):
    titles = [r["title"] for r in mem.recall(query, top_k=5)]
    assert expected in titles, f"{expected!r} missing from top-5: {titles}"
