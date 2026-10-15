"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.core.direction, aniseed_toolkit.scene.joints
"""
import warnings

from ..core.direction import Direction
from ..scene.joints import get_chain_facing_direction, get_upvector_direction

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.core.direction, aniseed_toolkit.scene.joints",
    DeprecationWarning,
    stacklevel=2,
)
