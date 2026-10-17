"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.sets
"""
import warnings

from ..scene.sets import add_to

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.sets",
    DeprecationWarning,
    stacklevel=2,
)
