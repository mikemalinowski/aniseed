"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.transforms
"""
import warnings

from ..scene.transforms import drive_from_local_matrix

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.transforms",
    DeprecationWarning,
    stacklevel=2,
)
