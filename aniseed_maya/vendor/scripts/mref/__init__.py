"""
mref is a small python wrapper which makes it easy to keep references and exposes
common functionality to objects.

Traits should always be accessed via the trait library and never imported directly.
You can access the Trait Singleton using mref.TraitLibrary.singleton() or you can
instance a new trait library if required using mref.TraitLibrary().
"""
from .core import get
from .core import find
from .core import create
from .core import selected
from .core import select
from .core import Trait
from .core import TraitLibrary
from .core import ReferencedItem
from .core import ReferenceList

from . import time
from . import constants
from . import wrapping

from maya import cmds
from maya import mel

def __getattr__(name):
    """
    Auto-resolve unknown ``mref`` attributes against ``maya.cmds``.

    Any attribute access on the ``mref`` package that doesn't match a
    defined name falls through to this function. If ``maya.cmds`` has a
    command of the same name, an auto-wrapped callable is returned that
    converts ``ReferencedItem`` / ``ReferenceList`` arguments to their
    full Maya names on the way in, and converts string results back to
    ``ReferencedItem`` instances on the way out. The net effect is that
    ``mref.foo(...)`` behaves like ``cmds.foo(...)`` for any cmds
    command, with transparent ReferencedItem support.

    Caveat: a typo of an ``mref`` function name that happens to collide
    with a cmds command silently routes to cmds instead of erroring.
    ``tests/test_init.py`` enforces that no name defined on ``mref``
    accidentally shadows a cmds command — see ``INTENTIONAL_SHADOWS``
    there for the explicit override list.
    """
    if hasattr(cmds, name):
        return wrapping.wrapped_cmds(name)

    raise AttributeError(f"{name} is not recognised in mref or cmds")
