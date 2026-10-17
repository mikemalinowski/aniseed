"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.core.naming
"""
import warnings

from ..core.naming import unique

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.core.naming",
    DeprecationWarning,
    stacklevel=2,
)
