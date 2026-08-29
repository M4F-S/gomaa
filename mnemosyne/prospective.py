"""Mnemosyne compatibility shim for gomaa.prospective."""
import warnings
warnings.warn("Importing from 'mnemosyne.prospective' is deprecated. Use 'gomaa.prospective' instead.", DeprecationWarning, stacklevel=2)
from gomaa.prospective import *  # noqa: F401, F403
