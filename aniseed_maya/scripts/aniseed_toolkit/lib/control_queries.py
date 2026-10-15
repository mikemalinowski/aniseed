"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rig.control
"""
import warnings

from ..rig.control import curve_controls, has_curve_shapes

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rig.control",
    DeprecationWarning,
    stacklevel=2,
)
