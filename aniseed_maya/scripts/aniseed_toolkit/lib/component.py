"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed.builders, aniseed.dialogs, aniseed.mixins.joint_chain
"""
import warnings


warnings.warn(
    f"{__name__} is deprecated, use aniseed.builders, aniseed.dialogs, aniseed.mixins.joint_chain",
    DeprecationWarning,
    stacklevel=2,
)

_LAZY = {
    'JointChainMixin': ('aniseed.mixins.joint_chain', 'JointChainMixin'),
    'add_twister': ('aniseed.builders', 'add_twister'),
    'mirror': ('aniseed.builders', 'mirror_component'),
    'request_count': ('aniseed.dialogs', 'request_count'),
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
