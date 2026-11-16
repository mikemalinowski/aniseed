"""
Provides the "Utility : Disable Segment Scale Compensation" component, which
turns off segmentScaleCompensate on every joint at or below a given node.
"""
import os
import logging
import mref
import aniseed

log = logging.getLogger(__name__)


class DisableSegmentScaleCompensation(aniseed.RigComponent):
    """
    Turns off segmentScaleCompensate on the given node (if it is a joint)
    and on every joint below it.

    With segment scale compensation on, a joint cancels its parent joint's
    scale, so a joint driven by a world space constraint ends up at the
    wrong world scale when the global control is scaled. Game engines do
    not honour the setting either, so turning it off keeps the rig and the
    exported skeleton scaling the same way.
    """

    identifier = "Utility : Disable Segment Scale Compensation"
    icon = os.path.join(os.path.dirname(__file__), "disable_segment_scale_compensation.png")

    def __init__(self, *args, **kwargs):
        """
        Declares the Root input, the node at or below which every joint
        is affected.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Root",
            value="",
            description=(
                "The node at or below which every joint has segment scale "
                "compensation turned off. This can be a joint or any "
                "transform, such as the skeleton org"
            ),
            validate=True,
        )

    def input_widget(self, requirement_name: str):
        """
        The root is picked with an object selector.
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        """
        Turns off segmentScaleCompensate on the root (if it is a joint) and
        on every joint below it.

        The root's existence is checked here rather than in is_valid, because
        the stack validates every component before running any, and the root
        (such as the skeleton org) is often created earlier in the same build.
        """
        root_name = self.input("Root").get()

        if not mref.objExists(root_name):
            log.warning(f"{self.label()}: The Root input ({root_name}) is not an existing node")
            return False

        root = mref.get(root_name)

        joints = root.children(node_type="joint", recursive=True)

        if root.node_type() == "joint":
            joints = [root] + joints

        for joint in joints:
            joint.attr("segmentScaleCompensate").set(False)

        return True
