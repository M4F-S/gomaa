"""Mnemosyne compatibility shim for gomaa.vault."""
import warnings
warnings.warn("Importing from 'mnemosyne.vault' is deprecated. Use 'gomaa.vault' instead.", DeprecationWarning, stacklevel=2)
from gomaa.vault import *  # noqa: F401, F403
