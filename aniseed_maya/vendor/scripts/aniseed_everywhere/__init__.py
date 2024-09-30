"""
AniseedX is a cross-application rigging tool built upon the xstack framework.

Note: AniseedX does interact with 3d applications. Part of its core Rig class
assumes the creation of objects, attributes and data. In order to do this in
an application agnostic way, it uses crosswalk.

Crosswalk is a lightweight python package which exposes a common set of functions
to perform tasks. This package handles the re-routing between applications and their
underlying api.

IMPORTANT NOTE: When implementing application specific components you DO NOT need
to use crosswalk at all. It is only used at the framwork level because the amount
of interaction is minimal.
"""
from .rig import Rig
from .component import RigComponent
from .config import RigConfiguration

from . import constants
from . import widgets
from . import app
from . import resources

__version__ = "0.1.10"