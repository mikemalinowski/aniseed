"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rigging.ikfk
"""
import warnings

from ...rigging.ikfk import create_ikfk_visibility, create_snap_groups

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rigging.ikfk",
    DeprecationWarning,
    stacklevel=2,
)
