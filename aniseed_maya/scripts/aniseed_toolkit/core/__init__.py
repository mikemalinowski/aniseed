"""
The lowest layer of the toolkit: helpers with no rigging concepts, such as
unit conversion, naming, maths, attribute utilities and selection queries.

Modules in this layer only import from the standard library, Maya and mref.
"""
from . import api
from . import attributes
from . import direction
from . import maths
from . import naming
from . import selection
from . import units

__all__ = [
    "api",
    "attributes",
    "direction",
    "maths",
    "naming",
    "selection",
    "units",
]


def __getattr__(name):
    # -- aniseed_toolkit.core used to be the module holding the tool registry,
    # -- so those names are still served from here
    from .. import registry
    from .. import utils

    if name == "utils":
        return utils
    if hasattr(registry, name) and name in ("Tool", "ToolBox", "run", "register", "tool"):
        return getattr(registry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")