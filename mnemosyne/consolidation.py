"""Mnemosyne compatibility shim for gomaa.consolidation."""
import warnings
warnings.warn("Importing from 'mnemosyne.consolidation' is deprecated. Use 'gomaa.consolidation' instead.", DeprecationWarning, stacklevel=2)
from gomaa.consolidation import *  # noqa: F401, F403
