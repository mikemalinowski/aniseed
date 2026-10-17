"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.constraints
"""
import warnings

from ..scene.constraints import remove_all

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.constraints",
    DeprecationWarning,
    stacklevel=2,
)
