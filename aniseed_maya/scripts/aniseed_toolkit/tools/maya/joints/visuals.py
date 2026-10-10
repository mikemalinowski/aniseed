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
        This will determine the positions for a bezier spline in order
        to keep the joints transforms.

        Args:
            joints: List of joints
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
        This will determine the positions for a bezier spline in order
        to keep the joints transforms.

        Args:
            joints: List of joints
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
                try:
                    joint.drawStyle.set(draw_style)
                except:
                    pass
