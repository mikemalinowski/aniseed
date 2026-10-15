"""
Rig building blocks: ik and ikfk setups, soft ik, foot roll, blend chains,
rotators and the facial control rig.

Modules in this layer may import from the core, scene and rig layers.
"""
from . import blend_chain
from . import facial
from . import foot
from . import ik
from . import ikfk
from . import rotator
from . import soft_ik
from . import two_bone_ikfk

from .blend_chain import BlendChain
from .blend_chain import create_blend_chain
from .rotator import create_rotator
from .soft_ik import create_multi_bone_soft_ik
from .soft_ik import create_two_bone_soft_ik
from .two_bone_ikfk import TwoBoneIKFK
from .two_bone_ikfk import create_two_bone_ikfk

__all__ = [
    "blend_chain",
    "facial",
    "foot",
    "ik",
    "ikfk",
    "rotator",
    "soft_ik",
    "two_bone_ikfk",
    "BlendChain",
    "create_blend_chain",
    "create_multi_bone_soft_ik",
    "create_rotator",
    "create_two_bone_ikfk",
    "create_two_bone_soft_ik",
    "TwoBoneIKFK",
]

# -- Old names for modules which moved or merged
_MOVED_MODULES = {
    "node_math": "aniseed_toolkit.scene.node_math",
    "softik": "aniseed_toolkit.rigging.soft_ik",
    "multi_bone_softik": "aniseed_toolkit.rigging.soft_ik",
}


def __getattr__(name):
    if name in _MOVED_MODULES:
        import warnings
        import importlib
        warnings.warn(
            f"{__name__}.{name} is deprecated, use {_MOVED_MODULES[name]}",
            DeprecationWarning,
            stacklevel=2,
        )
        return importlib.import_module(_MOVED_MODULES[name])

    from .._legacy import resolve
    return resolve(__name__, name)