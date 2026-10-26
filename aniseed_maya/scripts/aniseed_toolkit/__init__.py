"""
aniseed_toolkit provides general rigging functionality for aniseed components
and for riggers working directly in Maya.

The library is layered - each layer only uses the layers before it:

    core      naming, maths, attributes, selection, directions
    scene     transforms, joints, constraints, shapes, skin, surfaces, node maths
    rig       controls, guides, tagging, pinning, spaces, the pose mixer
    rigging   ik / ikfk / soft ik setups, foot roll, blend chains, twist /
              spline / ribbon setups, bone alignment, facial rig

The user facing tools built on this library live in the Rigging and
Animation toolkits (the aniseed_maya_rigging_toolkit and
aniseed_maya_animation_toolkit packages), which are built on aniseed.toolkits.
"""
from .resources import register_resource_path

from . import resources
from . import utils

from . import core
from . import scene
from . import rig
from . import rigging

__version__ = "5.0.0"
