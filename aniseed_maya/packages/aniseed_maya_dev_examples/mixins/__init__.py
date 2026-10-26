"""
Mixins used by the dev examples. A mixin adds optional behaviour to a
RigComponent and contributes its menu entries through ``mixin_functions``.

Compose alongside RigComponent, with RigComponent first:

    from aniseed_maya_dev_examples.mixins import LoggingMixin

    class MyComponent(aniseed.RigComponent, LoggingMixin):
        ...

See components/05_extending/ex13_using_a_mixin.py for a worked example.
"""
from .logging_mixin import LoggingMixin
