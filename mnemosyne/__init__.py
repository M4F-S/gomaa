"""
Mnemosyne backwards compatibility layer.
Redirects all imports to the 'gomaa' package.
"""
import warnings

warnings.warn(
    "The 'mnemosyne' package has been renamed to 'gomaa'. "
    "Please update your imports to 'import gomaa' or 'from gomaa import ...'.",
    DeprecationWarning,
    stacklevel=2,
)

from gomaa import *  # noqa: F401, F403
from gomaa.core import UnifiedMemorySystem  # noqa: F401
from gomaa.mcp_server import MCPServer  # noqa: F401
from gomaa.vault import VaultManager  # noqa: F401
from gomaa.embedder import Embedder  # noqa: F401
from gomaa.security import AdmissionControl  # noqa: F401
from gomaa.consolidation import ConsolidationEngine  # noqa: F401
from gomaa.prospective import ProspectiveMemory  # noqa: F401
from gomaa.adapters import MnemosyneMemory, MnemosyneMemoryHandler  # noqa: F401

__all__ = [
    "UnifiedMemorySystem",
    "MCPServer",
    "VaultManager",
    "Embedder",
    "AdmissionControl",
    "ConsolidationEngine",
    "ProspectiveMemory",
    "MnemosyneMemory",
    "MnemosyneMemoryHandler",
]
