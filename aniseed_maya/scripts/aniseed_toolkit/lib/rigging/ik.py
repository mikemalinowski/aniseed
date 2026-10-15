"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rigging.ik
"""
import warnings

from ...rigging.ik import create_ik_chain, create_rp_handle

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rigging.ik",
    DeprecationWarning,
    stacklevel=2,
)
