import aniseed
import aniseed_toolkit
import maya.cmds as mc
import maya.api.OpenMaya as om


class CalculateUpvectorPosition(aniseed_toolkit.Tool):

    identifier = "Calculate Upvector Position"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["point_a", "point_b", "point_c"]:
            return aniseed.widgets.ObjectSelector()
        
    def run(
        self,
        point_a: str = "",
        point_b: str = "",
        point_c: str = "",
        length: float = 0.5,
        create: bool = False,
    ):
        """
        Based on three points, this will calculate the position for an
        up-vector for the plane.

        Args:
            point_a: Start point (which can be a float list or a node name)
            point_b: End point (which can be a float list or a node name)
            point_c: Start point (which can be a float list or a node name)
            length: By default the vector will be multipled by the chain length
                but you can use this value to multiply that to make it further or
                shorter
            create: If true, a transform node will be created at the specified location

        Returns:
            MVector of the position in worldspace
        """
        return aniseed_toolkit.transformation.calculate_upvector_position(
            point_a=point_a,
            point_b=point_b,
            point_c=point_c,
            length=length,
            create=create,
        )
