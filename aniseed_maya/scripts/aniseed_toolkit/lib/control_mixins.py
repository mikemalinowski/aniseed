"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed.mixins.controls
"""
import warnings


warnings.warn(
    f"{__name__} is deprecated, use aniseed.mixins.controls",
    DeprecationWarning,
    stacklevel=2,
)

_LAZY = {
    'InsertControlMixin': ('aniseed.mixins.controls', 'InsertControlMixin'),
    'SingularControlMixin': ('aniseed.mixins.controls', 'SingularControlMixin'),
}


def __getattr__(name):
    # -- Names which moved into aniseed are resolved on first use so
    # -- that the toolkit never imports aniseed when it is loaded
    if name in _LAZY:
        import importlib
        module, attribute = _LAZY[name]
        return getattr(importlib.import_module(module), attribute)
    from .._legacy import resolve
    return resolve(__name__, name)
