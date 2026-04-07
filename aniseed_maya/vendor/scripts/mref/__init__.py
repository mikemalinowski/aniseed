"""
mref is a small python wrapper which makes it easy to keep references and exposes
common functionality to objects
"""
from .core import get
from .core import find
from .core import create
from .core import selected
from .core import select
from .core import Trait
from .core import ReferencedItem
from .core import ReferenceList

from . import time
from . import constants
from . import wrapping

from maya import cmds

# -- This will resolve any unknown property accessors
# -- as if they are maya cmds commands.
def __getattr__(name):
    if not hasattr(cmds, name):
        raise AttributeError(f"{name} is not recognised in mref or cmds")
    return wrapping.wrapped_cmds(name)
