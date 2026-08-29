"""Mnemosyne compatibility shim for gomaa.cli."""
import warnings
warnings.warn("Importing from 'mnemosyne.cli' is deprecated. Use 'gomaa.cli' instead.", DeprecationWarning, stacklevel=2)
from gomaa.cli import *  # noqa: F401, F403
