"""Ranking for per-turn recall — one implementation, used by the live service and the package.

Why this module exists: the recall service shipped as a standalone script while the package
carried a second copy with different constants. Two rankers means the behaviour measured in a
benchmark is not the behaviour an agent gets.

Design rules (all measured, see the project notes):

* Hybrid = reciprocal-rank fusion of semantic + keyword, computed on rows the store already
  returned. Read-only: every store call passes ``touch=False`` so a per-turn reader does not
  inflate ``access_count`` (which feeds ACT-R ranking and decay).
* Perishability is a property of the *note*, not of a word in its title: tags say it, and a
  snapshot body says it. Title keywords over-match ("… status report", "… drift knowledge").
* A perishable note is **demoted**, not evicted: the penalty is multiplicative on the fused
  score, so an old snapshot loses to a fresh peer but a store whose only answer is a snapshot
  still returns something.
* The canonical current-state note wins its own question: tag ``current-state`` earns a bonus,
  and process notes (``state-note``, ``process``) never earn the room bonus.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

RRF_K = 60
MAX_CONTENT_CHARS = 320
BUDGET_CHARS = 1000

GENERIC_ROOMS = {"general", "user-preferences", "sessions"}
PREFERENCE_HINTS = (
    "prefer", "preference", "how should", "how do you", "convention", "style",
    "remember", "always", "never", "you must", "you should",
)

PERISHABLE_TAGS = {"live-state", "live_state", "snapshot", "status", "stale"}
# Tags that mark a note as a rule even when its title sounds like a status report.
DURABLE_TAGS = {"user-preference", "rule", "doctrine", "process", "study", "policy", "convention"}
ROLE_TAGS = {"state-note", "process"}

SNAPSHOT_SHAPE = re.compile(
    r"\b(as of|state at|status at|still (pending|running|open)|currently (paused|pending))\b",
    re.IGNORECASE,
)
HAS_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2}|\d{1,2} \w+ 20\d{2})\b")

# Chosen by a sweep on the frozen benchmark (2026-11-22): 0.5 / 0.35 / 0.2.
# 0.35 keeps an aged snapshot out of the top slot without erasing it from the pool.
PERISHABLE_FACTOR = 0.35
PERISHABLE_FLOOR = 0.15
PERISHABLE_GRACE_DAYS = 3.0
PERISHABLE_FULL_DAYS = 60.0
CURRENT_STATE_BONUS = 1.5


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _tags(row: Dict[str, Any]) -> set:
    return {str(t).lower() for t in (row.get("tags") or [])}


def is_perishable(row: Dict[str, Any]) -> bool:
    """True when the note describes a moment in time rather than a durable fact."""
    tags = _tags(row)
    if "current-state" in tags:
        # The canonical live-state note is refreshed on every release; it is the current
        # fact by definition and must not be demoted by its own status tag.
        return False
    if tags & DURABLE_TAGS:
        return False
    if tags & PERISHABLE_TAGS:
        return True
    body = (row.get("content") or "")[:600]
    return bool(SNAPSHOT_SHAPE.search(body) and HAS_DATE.search(body))


def _age_days(row: Dict[str, Any], now: datetime) -> Optional[float]:
    stamp = row.get("created_at") or row.get("updated_at")
    if isinstance(stamp, str):
        try:
            stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(stamp, datetime):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return max((now - stamp).total_seconds() / 86400.0, 0.0)


def perishable_factor(age_days: Optional[float]) -> float:
    """Multiplicative demotion: none inside the grace window, floor from 60 days."""
    if age_days is None or age_days <= PERISHABLE_GRACE_DAYS:
        return 1.0
    span = min((age_days - PERISHABLE_GRACE_DAYS) / (PERISHABLE_FULL_DAYS - PERISHABLE_GRACE_DAYS), 1.0)
    return 1.0 + (PERISHABLE_FLOOR - 1.0) * span


def _ranked(rows: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    return {_norm(r.get("title") or ""): i for i, r in enumerate(rows, 1) if r.get("title")}


def _as_of(row: Dict[str, Any]) -> str:
    stamp = row.get("created_at") or row.get("updated_at")
    if isinstance(stamp, datetime):
        return stamp.date().isoformat()
    if isinstance(stamp, str) and HAS_DATE.match(stamp):
        return stamp[:10]
    return ""


def rank_rows(
    semantic_rows: Iterable[Dict[str, Any]],
    keyword_rows: Iterable[Dict[str, Any]],
    shared_rows: Iterable[Dict[str, Any]] = (),
    *,
    query: str = "",
    top_k: int = 4,
    now: Optional[datetime] = None,
    scoped_rows: Iterable[Dict[str, Any]] = (),
) -> List[Dict[str, Any]]:
    """Pure fusion + scoring over rows the caller already fetched."""
    now = now or datetime.now(timezone.utc)
    semantic_rows, keyword_rows = list(semantic_rows), list(keyword_rows)
    sem_rank, kw_rank = _ranked(semantic_rows), _ranked(keyword_rows)
    scoped_rank = _ranked(list(scoped_rows))

    rows: Dict[str, Dict[str, Any]] = {}
    for row in list(semantic_rows) + list(keyword_rows) + list(shared_rows) + list(scoped_rows):
        key = _norm(row.get("title") or "")
        if key and key not in rows:
            rows[key] = dict(row, _rrf=0.0)

    for key, row in rows.items():
        if key in sem_rank:
            row["_rrf"] += 1.0 / (RRF_K + sem_rank[key])
        if key in kw_rank:
            row["_rrf"] += 1.0 / (RRF_K + kw_rank[key])
        if key in scoped_rank:
            row["_rrf"] += 1.0 / (RRF_K + scoped_rank[key])

    pref_query = any(hint in (query or "").lower() for hint in PREFERENCE_HINTS)
    query_key = _norm(query)
    ranked: List[Dict[str, Any]] = []

    for row in rows.values():
        tags = _tags(row)
        if row.get("superseded_by") or "probe" in tags:
            continue
        score = row["_rrf"] * 100.0
        wing, room = (row.get("wing") or ""), (row.get("room") or "")

        # Bonuses first: perishability must be able to demote a boosted note.
        if wing in ("fleet", "shared"):
            score -= 3.0
        if room in GENERIC_ROOMS and not pref_query:
            score -= 2.0
        if room and _norm(room) in query_key and not (tags & ROLE_TAGS):
            score += 2.5
        if wing and _norm(wing) in query_key:
            score += 1.5
        if "current-state" in tags:
            score += CURRENT_STATE_BONUS

        age = _age_days(row, now)
        if age is not None:
            # Recency is a nudge, never the ranking: an additive bonus up to +1.0 on a
            # ~1.6-scale RRF score let a fresh but merely adjacent note beat the note that
            # actually answers the question (measured: cosine 0.528 beat 0.613). Bounded
            # multiplicative term keeps stale notes from winning ties without overriding
            # relevance; perishability is still handled by the demotion below.
            score *= 0.97 + 0.03 / (1.0 + age / 30.0)
        perishable = is_perishable(row)
        if perishable:
            score *= perishable_factor(age)

        row["_score"] = score
        row["_age_days"] = age
        row["_perishable"] = perishable
        ranked.append(row)

    ranked.sort(key=lambda r: r["_score"], reverse=True)
    return ranked[:max(1, top_k)]


def hybrid(
    db,
    shared_db,
    query: str,
    query_embedding: List[float],
    top_k: int = 4,
    include_shared: bool = False,
    embedder_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Fetch read-only rows from the store(s), then rank them."""
    wide = max(top_k * 3, 12)

    try:
        sem = db.search_semantic(query_embedding, wide, None, scope=None,
                                 embedder_id=embedder_id, touch=False)
        kw = db.search_keyword(query, wide, scope=None, touch=False)
    except TypeError:  # store predates the touch kwarg (rollout window)
        sem = db.search_semantic(query_embedding, wide, None, scope=None, embedder_id=embedder_id)
        kw = db.search_keyword(query, wide, scope=None)

    shared: List[Dict[str, Any]] = []
    if include_shared and shared_db is not None:
        try:
            shared = shared_db.search_semantic(query_embedding, wide, None, scope=None,
                                               embedder_id=embedder_id)
        except Exception:
            shared = []

    return rank_rows(sem, kw, shared, query=query, top_k=top_k, now=now,
                     scoped_rows=_scoped_rows(db, query, query_embedding, wide, embedder_id))


def _scoped_rows(db, query: str, query_embedding: List[float], wide: int,
                 embedder_id: Optional[str]) -> List[Dict[str, Any]]:
    """Extra arm: when the question names a room, rank that room's notes against it.

    Without this, a question like "what is the current state of gomaa" competes in one pile
    with every old note that merely mentions Gomaa, and the canonical note never reaches the
    candidate pool (measured: absent from the semantic top 18 on two agents).
    """
    needle = _norm(query)
    if len(needle) < 4:
        return []
    try:
        rooms = db.count_by_wing_room()
    except Exception:
        return []
    best = None
    for row in rooms or []:
        room, wing = _norm(row.get("room") or ""), row.get("wing") or ""
        if len(room) >= 4 and room in needle and (best is None or len(room) > len(best[1])):
            best = (wing, room, row.get("room"))
    if not best:
        return []
    wing, _key, room_name = best
    try:
        return db.search_semantic(query_embedding, wide, None,
                                  scope={"wing": wing, "room": room_name},
                                  embedder_id=embedder_id, touch=False)
    except TypeError:
        try:
            return db.search_semantic(query_embedding, wide, None,
                                      scope={"wing": wing, "room": room_name},
                                      embedder_id=embedder_id)
        except Exception:
            return []
    except Exception:
        return []


def format_block(rows: List[Dict[str, Any]], budget_chars: int = BUDGET_CHARS) -> Tuple[str, List[str]]:
    """Render the block and return the titles actually rendered (truncation drops a title)."""
    lines: List[str] = []
    rendered: List[str] = []
    used = 0
    for row in rows:
        title = (row.get("title") or "").strip()
        body = re.sub(r"\s+", " ", (row.get("content") or "")).strip()
        if len(body) > MAX_CONTENT_CHARS:
            body = body[:MAX_CONTENT_CHARS].rstrip() + "…"
        scope = "/".join(p for p in (row.get("wing"), row.get("room")) if p)
        stamp = ""
        if row.get("_perishable"):
            as_of = _as_of(row)
            stamp = f" [as of {as_of}]" if as_of else ""
        line = f"- {title}{stamp}" + (f" ({scope})" if scope else "") + (f": {body}" if body else "")
        if used + len(line) + 1 > budget_chars:
            break
        lines.append(line)
        rendered.append(title)
        used += len(line) + 1
    if not lines and rows:
        # A budget smaller than one bullet must still return its beginning: an empty block
        # reads as "no memory" to the agent, which is a different (and wrong) answer.
        first = next((r for r in rows if (r.get("title") or "").strip()), None)
        if first is not None:
            title = (first.get("title") or "").strip()
            body = re.sub(r"\s+", " ", (first.get("content") or "")).strip()
            lines.append(f"- {title}: {body}"[:budget_chars].rstrip())
            rendered.append(title)
    return "\n".join(lines), rendered


def block_with_header(rows: List[Dict[str, Any]], budget_chars: int = BUDGET_CHARS) -> Tuple[str, List[str]]:
    block, rendered = format_block(rows, budget_chars)
    return (f"Relevant stored notes:\n{block}" if block else ""), rendered


__all__ = [
    "hybrid", "format_block", "block_with_header", "is_perishable", "perishable_factor",
    "CURRENT_STATE_BONUS", "PERISHABLE_FACTOR", "PERISHABLE_FLOOR", "RRF_K",
]
