"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.surfaces
"""
import warnings

from ..scene.surfaces import construct, serialise

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.surfaces",
    DeprecationWarning,
    stacklevel=2,
)
