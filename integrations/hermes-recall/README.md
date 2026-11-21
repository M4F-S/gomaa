# Hermes recall service (deployed)

This is the service the five Hermes agents actually run on `127.0.0.1:8790`, committed here so the
running code is versioned instead of existing only as a copied script.

Differences from `gomaa/recall_service.py`: this launcher reads the DSN/vault values out of
`/opt/data/mcp-servers/obsidian_memory_mcp.py`, inserts `/opt/data/gomaa-live` on Old, and logs to
`/opt/data/logs/gomaa-recall.jsonl`. Ranking logic is kept in sync manually until the two
implementations are unified (planned: `gomaa.recall_service` + a thin launcher).

Deploy: copy to `/opt/data/scripts/gomaa_recall_service.py` in each container, then restart the
process. Backups live in `/opt/data/backups/gomaa/`.
