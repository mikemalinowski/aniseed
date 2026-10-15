"""
Defines the "Stack : Organiser" component. It builds nothing and exists only
to group other components beneath it in the stack, keeping large rigs
readable (e.g. "Rig Hierarchy", "Post Build" and "Construct Layers" in the
default stack).
"""
import os
import aniseed


# --------------------------------------------------------------------------------------
class OrganiserComponent(aniseed.RigComponent):
    """
    Does nothing when built - it exists purely to group other components
    beneath it in the stack.
    """

    identifier = "Stack : Organiser"
    icon = os.path.join(
        os.path.dirname(__file__),
        "organiser.png",
    )
