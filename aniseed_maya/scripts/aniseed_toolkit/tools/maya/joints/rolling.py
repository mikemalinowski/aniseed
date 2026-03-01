import aniseed
import aniseed_toolkit
import maya.cmds as mc


class RollJoints(aniseed_toolkit.Tool):

    identifier = "Roll Joints"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name == "joints":
            return aniseed.widgets.ObjectList()
        if keyword_name == "axis":
            return aniseed.widgets.ItemSelector(default_item="x", items=["x", "y", "z"])

    def run(self, joints: list[str] = None, axis="x", value=90) -> None:
        """
        Moves the rotations on the given joints to the joint orients
        attributes (zeroing the rotations).

        Args:
            joints: List of joints to move the rotation attributes for

        Returns:
            None
        """
        if isinstance(joints, str):
            joints = [joints]

        if not joints:
            joints = mc.ls(sl=True)

        if not joints:
            return

        return aniseed_toolkit.joints.roll(joints, axis, value)
