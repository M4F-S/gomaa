"""Gomaa v4.0.0 (Gomaa Neo) - Cognitive Quadrant Memory & HippoRAG 2 Platform for AI Agents."""

from .backup import BackupManager
from .core import UnifiedMemorySystem
from .hipporag import HippoRAGEngine

__version__ = "4.0.0"
__all__ = ["UnifiedMemorySystem", "HippoRAGEngine", "BackupManager", "__version__"]
