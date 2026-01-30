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
        positions = list()
        degree = 1

        points = [
            mc.xform(
                joint,
                query=True,
                translation=True,
                worldSpace=True,
            )
            for joint in joints
        ]

        knots = [
            i
            for i in range(len(points) + degree - 1)
        ]

        mc.curve(
            p=points,
            degree=degree,
            knot=knots
        )

        quad_curve = mc.rebuildCurve(
            replaceOriginal=True,
            rebuildType=0,  # Uniform
            endKnots=1,
            keepRange=False,
            keepEndPoints=True,
            keepTangents=False,
            spans=1,
            degree=3,
            tolerance=0.01,
        )[0]

        cv_count = mc.getAttr(f"{quad_curve}.spans") + mc.getAttr(f"{quad_curve}.degree")

        for cv_index in range(cv_count):
            position = mc.xform(
                f"{quad_curve}.cv[{cv_index}]",
                q=True,
                t=True,
                ws=True,
            )
            positions.append(position)

        mc.delete(quad_curve)
        return positions
