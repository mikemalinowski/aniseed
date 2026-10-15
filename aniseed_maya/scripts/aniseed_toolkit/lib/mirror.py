"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.mirror
"""
import warnings

from ..scene.mirror import MIRROR_PLANES, global_mirror, invert_translation

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.mirror",
    DeprecationWarning,
    stacklevel=2,
)
