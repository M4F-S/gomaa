"""Mnemosyne compatibility shim for gomaa.security."""
import warnings
warnings.warn("Importing from 'mnemosyne.security' is deprecated. Use 'gomaa.security' instead.", DeprecationWarning, stacklevel=2)
from gomaa.security import *  # noqa: F401, F403
