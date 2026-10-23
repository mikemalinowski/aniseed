import mref
import aniseed_toolkit


class SetJointDrawStyle(aniseed_toolkit.Tool):
    identifier = "Set Draw Style"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(
            self,
            visible: bool = True,
    ):
        """
        This will show or hide the bones of the selected joints by setting
        their draw style.

        Args:
            visible: If true the bones are shown, otherwise they are hidden
        """
        draw_style = 0  # -- Show the bone
        if not visible:
            draw_style = 2  # -- Hidden

        for node in mref.selected():
            if node.has_attribute("drawStyle"):
                node.drawStyle.set(draw_style)


class SetJointHierarchyDrawStyle(aniseed_toolkit.Tool):
    identifier = "Set Draw Style (Hierarchy)"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(
            self,
            visible: bool = True,
    ):
        """
        This will show or hide the bones of the selected joints, and of
        every joint below them, by setting their draw style.

        Args:
            visible: If true the bones are shown, otherwise they are hidden
        """
        draw_style = 0  # -- Show the bone
        if not visible:
            draw_style = 2  # -- Hidden

        joints = []

        for node in mref.selected():
            joints.append(node)
            joints.extend(node.children(recursive=True, node_type="joint"))

        for joint in joints:
            if joint.has_attribute("drawStyle"):
                # -- Locked or connected draw styles are left as they are
                try:
                    joint.drawStyle.set(draw_style)
                except RuntimeError:
                    pass
