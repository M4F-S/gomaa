"""Mnemosyne compatibility shim for gomaa.embedder."""
import warnings
warnings.warn("Importing from 'mnemosyne.embedder' is deprecated. Use 'gomaa.embedder' instead.", DeprecationWarning, stacklevel=2)
from gomaa.embedder import *  # noqa: F401, F403
