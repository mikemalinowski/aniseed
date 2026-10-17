"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rigging.facial
"""
import warnings

from ..rigging.facial import FacialControlRig

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rigging.facial",
    DeprecationWarning,
    stacklevel=2,
)
