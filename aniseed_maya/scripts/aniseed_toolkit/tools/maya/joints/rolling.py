import aniseed
import aniseed_toolkit
from maya import cmds


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
        Rolls each of the given joints around one of its own local axes by
        the given amount, keeping the world transforms of its children.

        Args:
            joints: List of joints to roll. If none are given then the
                selection will be used
            axis: The local axis to roll around: "x", "y" or "z"
            value: The amount to roll by, in degrees

        Returns:
            None
        """
        if isinstance(joints, str):
            joints = [joints]

        if not joints:
            joints = cmds.ls(sl=True)

        if not joints:
            return

        return aniseed_toolkit.scene.joints.roll(joints, axis, value)
