"""Encoder provenance helpers — model identity, independent of where it ran.

A vector only means something to the model that produced it. It does *not* matter
whether that model ran in this process (``st:``), behind the embed microservice
(``remote:``) or was written by an older deployment under a different prefix: the
same weights produce comparable vectors, so they must compare equal.

``hash-v1`` is not a model — it is a deterministic SHA-256 projection with no
semantic content — and must never match anything but itself.
"""

from __future__ import annotations

from typing import Optional

# Prefixes that only say *where* the encoder ran, not *what* it was.
_TRANSPORT_PREFIXES = {"remote", "st", "local", "st-http", "http", "remote-http"}


def normalise_model_id(value: Optional[str]) -> str:
    """Return the comparable model identity of an encoder tag.

    ``remote:all-MiniLM-L6-v2``      -> ``all-minilm-l6-v2``
    ``st:sentence-transformers/all-MiniLM-L6-v2`` -> ``all-minilm-l6-v2``
    ``all-MiniLM-L6-v2``             -> ``all-minilm-l6-v2``
    ``hash-v1`` / ``None`` / ``""``  -> ``""`` (never equal to a real model)
    """
    text = (value or "").strip().lower()
    if not text or text.startswith("hash"):
        return ""
    if ":" in text:
        prefix, _, rest = text.partition(":")
        if prefix in _TRANSPORT_PREFIXES and rest:
            text = rest
    return text.rsplit("/", 1)[-1]


def same_encoder(a: Optional[str], b: Optional[str]) -> bool:
    """True when two tags name the same model (``None`` means unknown, not equal)."""
    left, right = normalise_model_id(a), normalise_model_id(b)
    return bool(left) and left == right
