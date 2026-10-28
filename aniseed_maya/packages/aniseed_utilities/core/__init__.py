"""
The lowest layer of the toolkit: helpers with no rigging concepts, such as
naming, maths, attribute utilities and selection queries.

Modules in this layer only import from the standard library, Maya and mref.
"""
from . import api
from . import attributes
from . import direction
from . import maths
from . import naming
from . import selection

__all__ = [
    "api",
    "attributes",
    "direction",
    "maths",
    "naming",
    "selection",
]