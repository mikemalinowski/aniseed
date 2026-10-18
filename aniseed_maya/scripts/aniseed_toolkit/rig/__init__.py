"""
Rig concepts: controls, guides, tagging, pinning, spaces and the pose mixer.

Modules in this layer may import from the core and scene layers.

For compatibility, the functions which used to live in the old
aniseed_toolkit.rig module (all_controls, get, ...) are also available here.
"""
from . import component_outputs
from . import control
from . import controls
from . import guide
from . import pinning
from . import pose_mixer
from . import space
from . import tagging

from .controls import all_controls
from .controls import controls_by_location
from .controls import get
from .controls import get_rig_node
from .controls import mirror_control_shapes
from .controls import opposing_controls

__all__ = [
    "component_outputs",
    "control",
    "controls",
    "guide",
    "pinning",
    "pose_mixer",
    "space",
    "tagging",
    "all_controls",
    "controls_by_location",
    "get",
    "get_rig_node",
    "mirror_control_shapes",
    "opposing_controls",
]