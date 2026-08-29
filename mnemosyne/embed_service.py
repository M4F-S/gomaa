"""Mnemosyne compatibility shim for gomaa.embed_service."""
import warnings
warnings.warn("Importing from 'mnemosyne.embed_service' is deprecated. Use 'gomaa.embed_service' instead.", DeprecationWarning, stacklevel=2)
from gomaa.embed_service import *  # noqa: F401, F403
