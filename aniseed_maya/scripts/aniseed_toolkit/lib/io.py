"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.hierarchy_io (the file read
and write functions, which prompt for anything not given, are in
aniseed_toolkit.ui.dialogs)
"""
import warnings

from ..scene.hierarchy_io import SUPPORTED_TYPES, dict_to_hierarchy, get_supported_io_types, hierarchy_to_dict

_INTERACTIVE = ["load_hierarchy_file", "write_hierarchy_file"]

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.hierarchy_io",
    DeprecationWarning,
    stacklevel=2,
)


def __getattr__(name):
    # -- The interactive versions (which prompt for anything not given) live
    # -- in the ui layer, which imports Qt, so they are resolved on first use
    if name in _INTERACTIVE:
        from ..ui import dialogs
        return getattr(dialogs, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")