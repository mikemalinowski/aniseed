"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed.builders, aniseed_toolkit.rig.space
"""
import warnings

from ..rig.space import get_root_control

warnings.warn(
    f"{__name__} is deprecated, use aniseed.builders, aniseed_toolkit.rig.space",
    DeprecationWarning,
    stacklevel=2,
)

_LAZY = {
    'add_space_switch': ('aniseed.builders', 'add_space_switch'),
    'setup_fk_transform_worldspace_switches': ('aniseed.builders', 'setup_fk_transform_worldspace_switches'),
    'setup_fk_worldspace_switches': ('aniseed.builders', 'setup_fk_worldspace_switches'),
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
