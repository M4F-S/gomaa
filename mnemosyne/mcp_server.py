"""Mnemosyne compatibility shim for gomaa.mcp_server."""
import warnings
warnings.warn("Importing from 'mnemosyne.mcp_server' is deprecated. Use 'gomaa.mcp_server' instead.", DeprecationWarning, stacklevel=2)
from gomaa.mcp_server import *  # noqa: F401, F403
