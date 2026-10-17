"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.transforms
"""
import warnings

from ..scene.transforms import create, create_locator_at_center

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.transforms",
    DeprecationWarning,
    stacklevel=2,
)
