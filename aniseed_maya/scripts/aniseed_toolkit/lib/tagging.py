"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rig.tagging
"""
import warnings

from ..rig.tagging import all_children, find_all, get_first_child, get_tags, has_tag, tag

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rig.tagging",
    DeprecationWarning,
    stacklevel=2,
)
