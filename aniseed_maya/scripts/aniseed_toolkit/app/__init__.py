"""
Deprecated package, kept for compatibility until aniseed_toolkit 4.0. The
toolkit app now lives in aniseed_toolkit.ui.app.
"""
import importlib


def __getattr__(name):
    if name == "widgets":
        return importlib.import_module(f"{__name__}.widgets")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")