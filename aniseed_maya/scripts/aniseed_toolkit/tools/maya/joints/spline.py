import aniseed
import aniseed_toolkit
import maya.cmds as mc



class CalculateFourPointSplineFromJoints(aniseed_toolkit.Tool):

    identifier = "Calculate Four Spline Positions From Joints"
    classification = "Rigging"
    categories = [
        "Rigging",
    ]
    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name == "joints":
            return aniseed.widgets.ObjectList()
        
    def run(
        self,
        joints: str = "",
    ):
        """
        This will determine the positions for a bezier spline in order
        to keep the joints transforms.

        Args:
            joints: List of joints
        """
        return aniseed_toolkit.transformation.calculate_four_point_spline_positions(
            nodes=joints,
        )
