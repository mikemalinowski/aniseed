"""
Deprecated package, kept for compatibility until aniseed_toolkit 4.0.

The modules which used to live here have moved into the core, scene, rig
and rigging packages (and the aniseed component support into aniseed).
Each old module is still importable from here and re-exports its old names.
"""
import importlib


def __getattr__(name):
    try:
        return importlib.import_module(f"{__name__}.{name}")
    except ModuleNotFoundError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
