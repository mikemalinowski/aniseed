"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rig.controls
"""
import warnings

from ..rig.controls import all_controls, controls_by_location, get, get_rig_node, opposing_controls

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rig.controls",
    DeprecationWarning,
    stacklevel=2,
)
