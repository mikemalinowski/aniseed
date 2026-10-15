"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rigging.rotator
"""
import warnings

from ...rigging.rotator import create_rotator

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rigging.rotator",
    DeprecationWarning,
    stacklevel=2,
)
