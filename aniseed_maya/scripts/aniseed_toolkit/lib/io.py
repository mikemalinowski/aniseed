"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.hierarchy_io
"""
import warnings

from ..scene.hierarchy_io import SUPPORTED_TYPES, dict_to_hierarchy, get_supported_io_types, hierarchy_to_dict, load_hierarchy_file, write_hierarchy_file

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.hierarchy_io",
    DeprecationWarning,
    stacklevel=2,
)
