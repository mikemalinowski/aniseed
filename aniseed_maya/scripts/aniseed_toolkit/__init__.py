"""
aniseed_toolkit provides general rigging functionality for aniseed components
and for riggers working directly in Maya.

The library is layered - each layer only uses the layers before it:

    core      units, naming, maths, attributes, selection, directions
    scene     transforms, joints, constraints, shapes, skin, surfaces, node maths
    rig       controls, guides, tagging, pinning, spaces, the pose mixer
    rigging   ik / ikfk / soft ik setups, foot roll, blend chains, twist /
              spline / ribbon setups, bone alignment, facial rig

User facing tools (the actions shown in the toolkit app, and available through
`run("<tool name>")`) are registered with the `@tool` decorator or by
subclassing `Tool` - see the registry module.

Modules which existed before this layout (aniseed_toolkit.joints,
aniseed_toolkit.transformation, ...) are still available, with a deprecation
warning, until aniseed_toolkit 4.0.
"""
import importlib

from .registry import Tool
from .registry import ToolBox
from .registry import run
from .registry import register
from .registry import tool
from .resources import register_resource_path

from . import registry
from . import resources
from . import utils

from . import core
from . import scene
from . import rig
from . import rigging

__version__ = "3.2.0"

def launch(*args, **kwargs):
    """
    Launches the toolkit app. The ui is only imported when it is launched.
    """
    from .ui.app import launch as _launch
    return _launch(*args, **kwargs)


# -- Modules which used to be available directly on the package. They are
# -- served by the compatibility shims in aniseed_toolkit.lib.
_OLD_MODULES = [
    "attributes",
    "component",
    "component_outputs",
    "constraints",
    "containts",
    "control",
    "control_queries",
    "direction",
    "facial_controls",
    "guide",
    "io",
    "joints",
    "matrix_drive",
    "mirror",
    "mutils",
    "naming",
    "offset_controls",
    "option_files",
    "pinning",
    "sets",
    "shapes",
    "skin",
    "space",
    "stack_joints",
    "surfaces",
    "tagging",
    "transformation",
    "transforms",
    "units",
    "visibility",
]


def __getattr__(name):
    if name in _OLD_MODULES:
        return importlib.import_module(f"{__name__}.lib.{name}")

    # -- The shared tool box is created on first use. Creating it discovers the
    # -- tools (executing their modules, which import Qt), so the library can
    # -- be imported without the tools or Qt.
    if name == "tools":
        return ToolBox.singleton()

    if name in ("app", "lib", "ui"):
        return importlib.import_module(f"{__name__}.{name}")

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
