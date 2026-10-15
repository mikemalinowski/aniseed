"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rigging.soft_ik
"""
import warnings

from ...rigging.soft_ik import create_multi_bone_soft_ik

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rigging.soft_ik",
    DeprecationWarning,
    stacklevel=2,
)
