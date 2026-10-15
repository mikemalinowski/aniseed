"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rigging.foot
"""
import warnings

from ...rigging.foot import DEFAULT_GUIDE_TRANSFORMS, MAX_ROLL, PIVOT_TAGS, ROLL_AXES, ROLL_AXIS_OPTIONS, create_guides, create_pivots, create_roll

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rigging.foot",
    DeprecationWarning,
    stacklevel=2,
)
