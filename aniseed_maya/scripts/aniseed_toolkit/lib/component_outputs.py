"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed.component_outputs
"""
import warnings


warnings.warn(
    f"{__name__} is deprecated, use aniseed.component_outputs",
    DeprecationWarning,
    stacklevel=2,
)

_LAZY = {
    'clear_outputs': ('aniseed.component_outputs', 'clear_outputs'),
    'declare_joint_outputs': ('aniseed.component_outputs', 'declare_joint_outputs'),
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
