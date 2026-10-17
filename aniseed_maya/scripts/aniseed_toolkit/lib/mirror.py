"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.mirror (global_mirror, which
prompts for anything not given, is aniseed_toolkit.ui.dialogs.global_mirror)
"""
import warnings

from ..scene.mirror import MIRROR_PLANES, invert_translation

_INTERACTIVE = ["global_mirror"]

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.mirror",
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