"""
Mixins that add optional capabilities to a RigComponent. Each mixin is
self-contained and contributes its user-facing actions via xstack's
``mixin_functions`` extension point -- so the framework never has to know
about any specific mixin type.

Compose alongside RigComponent:

    from aniseed_maya_standard.mixins import MirrorMixin

    class Arm(aniseed.RigComponent, MirrorMixin):
        ...
"""
from .mirroring import MirrorMixin
