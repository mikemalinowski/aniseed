"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rig.pinning
"""
import warnings

from ..rig.pinning import get_pin, get_pinned_nodes, is_pinned, pin, pin_hierarchy, remove_all_pins, remove_pins

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rig.pinning",
    DeprecationWarning,
    stacklevel=2,
)
