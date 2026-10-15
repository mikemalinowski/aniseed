"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.constraints
"""
import warnings

from ..scene.constraints import blend_weights, parent_and_scale

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.constraints",
    DeprecationWarning,
    stacklevel=2,
)
