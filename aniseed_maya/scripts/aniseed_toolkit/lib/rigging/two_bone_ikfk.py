"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rigging.two_bone_ikfk
"""
import warnings

from ...rigging.two_bone_ikfk import TwoBoneIKFK, create_two_bone_ikfk, unique_name

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rigging.two_bone_ikfk",
    DeprecationWarning,
    stacklevel=2,
)
