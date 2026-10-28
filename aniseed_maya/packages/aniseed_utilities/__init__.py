"""
aniseed_utilities is an aniseed package providing general rigging
functionality for aniseed components and for riggers working directly in
Maya, along with the general utility components and the Maya host.

The library is layered - each layer only uses the layers before it:

    core      naming, maths, attributes, selection, directions
    scene     transforms, joints, constraints, shapes, skin, surfaces, node maths
    rig       controls, guides, tagging, pinning, spaces, the pose mixer
    mixins    optional component capabilities, such as MirrorMixin
    ui        dialogs (imports Qt, so it is not imported with the package -
              import aniseed_utilities.ui.dialogs explicitly)

Rig building blocks (ik / ikfk / soft ik setups, foot roll, twist, spline and
ribbon setups...) live in aniseed_standard.rigging.

Code outside this package imports it as:

    import aniseed_utilities as au

    au.rig.control.create(...)

Nothing in this package may import any other aniseed package.
"""
from .resources import register_resource_path

from . import resources
from . import utils

from . import core
from . import scene
from . import rig
from . import mixins
