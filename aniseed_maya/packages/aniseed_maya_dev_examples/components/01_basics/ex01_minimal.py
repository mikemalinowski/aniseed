"""
Provides the "Dev Example : Minimal" component. This is the smallest component
aniseed can load and build, and is the place to start reading.

What this example teaches:
    * A component only needs an identifier and a run method
    * What run's return value means to the build

Read next: ex02_options_and_inputs.py
"""
import logging

# -- aniseed gives us RigComponent, the base class every component inherits from
import aniseed

log = logging.getLogger(__name__)


class MinimalComponent(aniseed.RigComponent):
    """
    The smallest possible component. It logs a message when the rig builds
    and does nothing else.
    """

    # -- Key idea: the identifier is how aniseed finds this class in its
    # -- component library, and it is what gets written into the rig recipe.
    # -- It must be unique across every aniseed package, and must not change
    # -- once rigs use it, or those rigs will load it as a missing component.
    identifier = "Dev Example : Minimal"

    # -- Note that the class docstring above is shown to the user as the help
    # -- text in the app, so write it for riggers rather than for developers.

    def run(self):
        """
        Called when the rig builds. Returning None or True is a success,
        returning exactly False fails the build, and raising an exception
        fails the build and records the traceback (see ex03_validation.py).
        """
        # -- self.label() is the name the user gave this instance in the stack.
        # -- self.rig is the Rig (stack) this component belongs to, and
        # -- self.rig.label is the name of the node in the scene holding it.
        log.info(f"{self.label()} ran as part of {self.rig.label}")
