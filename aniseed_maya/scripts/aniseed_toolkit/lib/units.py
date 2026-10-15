"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.core.units
"""
import warnings

from ..core.units import cm_to_unit, from_cm, matrix_from_cm, matrix_to_cm, to_cm, unit_to_cm

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.core.units",
    DeprecationWarning,
    stacklevel=2,
)
