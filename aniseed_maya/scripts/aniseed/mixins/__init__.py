"""
Mixins that add optional capabilities to a RigComponent. Each mixin is
self-contained and contributes its user-facing actions via xstack's
``mixin_functions`` extension point -- so the framework never has to know
about any specific mixin type.

Compose alongside RigComponent (mixin FIRST, so MRO ordering finds the
mixin's contributions before RigComponent's):

    from aniseed.mixins.mirroring import MirrorMixin

    class Arm(MirrorMixin, RigComponent):
        ...
"""
from .mirroring import MirrorMixin
