from .blend_chain import BlendChain
from .blend_chain import create_blend_chain
from .two_bone_ikfk import TwoBoneIKFK
from .two_bone_ikfk import create_two_bone_ikfk

from .softik import create_two_bone_soft_ik
from .multi_bone_softik import create_multi_bone_soft_ik
from .rotator import create_rotator

from . import ik
from . import ikfk
from . import foot
from . import node_math

def __getattr__(name):
    # -- Deprecated names are still served from the legacy package
    from ..._legacy import resolve
    return resolve(__name__, name)
