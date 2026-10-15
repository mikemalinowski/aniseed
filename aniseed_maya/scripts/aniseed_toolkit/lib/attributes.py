"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.core.attributes
"""
import warnings

from ..core.attributes import add_separator, lock_and_hide

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.core.attributes",
    DeprecationWarning,
    stacklevel=2,
)
