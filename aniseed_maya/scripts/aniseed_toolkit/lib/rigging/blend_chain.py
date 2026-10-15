"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rigging.blend_chain
"""
import warnings

from ...rigging.blend_chain import BlendChain, create_blend_chain

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rigging.blend_chain",
    DeprecationWarning,
    stacklevel=2,
)
