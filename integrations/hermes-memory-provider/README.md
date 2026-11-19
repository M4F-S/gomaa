# Hermes memory provider for Gomaa

The client half of `gomaa/recall_service.py`: a drop-in memory provider for [Hermes Agent](https://hermes-agent.nousresearch.com/docs)
that gives the model recalled notes **during** a conversation, not only at session start.

`gomaa_provider.py` is dependency-free on the Gomaa side — it speaks HTTP to the recall service,
because the Hermes gateway venv has no psycopg2, numpy or sentence-transformers.

## Install (per agent)

```bash
# 1. the service, where the memory stack lives (cold start ~19 s: load the encoder once)
python -m gomaa.recall_service --host 127.0.0.1 --port 8790 --log /var/log/gomaa-recall.jsonl

# 2. the provider
mkdir -p "$HERMES_HOME/plugins/gomaa"
cp gomaa_provider.py "$HERMES_HOME/plugins/gomaa/__init__.py"
printf 'name: gomaa\nversion: 1.0.0\ndescription: "Gomaa per-turn recall via the local recall service"\n' \
    > "$HERMES_HOME/plugins/gomaa/plugin.yaml"

# 3. select it (one external provider at a time; the built-in store stays active)
hermes config set memory.provider gomaa

# 4. reload
s6-svc -r /run/service/gateway-default     # or restart the gateway the way your install does
```

Verify with a question whose answer lives only in memory, asked **mid-conversation** — the first
message of a session proves nothing about the per-turn hook.

## How it behaves

| hook | what it does |
|---|---|
| `queue_prefetch(query)` | background `POST /recall` after a turn; result cached per session |
| `prefetch(query)` | returns the cached block (TTL 900 s, Jaccard ≥ 0.30), else one bounded live call |
| dedupe | titles already injected in this session are dropped, so a stable topic injects once |
| budget | block capped at 1200 chars (4 notes, 1000-char service budget) |
| `recall_status()` | 🧠 indicator with the note count, so the user sees memory was used |
| `system_prompt_block()` | empty — the built-in provider already injects the profile |
| `get_tool_schemas()` | none — a separate MCP server already publishes the `memory_*` tools |

Two properties of the Hermes hook drive this shape: `prefetch()` blocks the turn (and is skipped
while a previous call is still running), and its output is stamped into the user row and replayed on
every later request. Hence the cache, the small block, and the dedupe.

## Notes

- Read timeout is 2.5 s: measured cold queries ranged 0.3–1.4 s across hosts, and a 0.9 s timeout
  silently dropped real answers (fail-open returns an empty block, which looks like "no notes").
- Supervise the service with a watchdog whose readiness window is ≥ 2× the measured cold start, and
  start it outside the agent's process group — otherwise the first agent restart leaves it dead.
