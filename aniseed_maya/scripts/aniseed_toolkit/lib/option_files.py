"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed.dialogs
"""
import warnings


warnings.warn(
    f"{__name__} is deprecated, use aniseed.dialogs",
    DeprecationWarning,
    stacklevel=2,
)

_LAZY = {
    'clear_option': ('aniseed.dialogs', 'clear_option'),
    'load_json_file': ('aniseed.dialogs', 'load_json_file'),
    'save_json_file': ('aniseed.dialogs', 'save_json_file'),
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
