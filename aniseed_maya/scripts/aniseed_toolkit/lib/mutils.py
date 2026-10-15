"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.core.api, aniseed_toolkit.core.selection
"""
import warnings

from ..core.api import get_dagpath, get_mobject, get_name
from ..core.selection import first_selected

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.core.api, aniseed_toolkit.core.selection",
    DeprecationWarning,
    stacklevel=2,
)
