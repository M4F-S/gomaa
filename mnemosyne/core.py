"""Mnemosyne compatibility shim for gomaa.core."""
import warnings
warnings.warn("Importing from 'mnemosyne.core' is deprecated. Use 'gomaa.core' instead.", DeprecationWarning, stacklevel=2)
from gomaa.core import *  # noqa: F401, F403
