"""
Defines the "Rig Configuration : Snake" component. It is a placeholder rig
configuration which currently inherits all of its naming and default stack
behaviour from the base aniseed RigConfiguration, so projects can adopt it
now and diverge from the standard configuration later.
"""
import aniseed


class LowerStandardConfig(aniseed.RigConfiguration):
    """
    Placeholder configuration registered under its own identifier so
    that projects can adopt ``Rig Configuration : Snake`` up front and
    then diverge from the standard config later without having to
    migrate existing stacks over to a different component type.

    Currently inherits all behaviour (location tokens, classification
    tokens, name format, default stack creation) from
    :class:`aniseed.RigConfiguration` unchanged.
    """

    identifier = "Rig Configuration : Snake"