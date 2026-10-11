"""Backwards compatibility shim for mnemosyne.hipporag."""
from gomaa.hipporag import *  # noqa: F401, F403
from gomaa.hipporag import HippoRAGEngine  # noqa: F401

__all__ = ["HippoRAGEngine"]
