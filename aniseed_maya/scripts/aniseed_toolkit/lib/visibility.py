"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.visibility
"""
import warnings

from ..scene.visibility import hide, show

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.visibility",
    DeprecationWarning,
    stacklevel=2,
)
