import aniseed_toolkit
import maya.cmds as mc
import maya.api.OpenMaya as om


class CalculateUpvectorPosition(aniseed_toolkit.Tool):

    identifier = "Calculate Upvector Position"
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

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

        if not point_a:
            point_a = mc.ls(sl=True)[0]

        if not point_b:
            point_b = mc.ls(sl=True)[1]

        if not point_c:
            point_c = mc.ls(sl=True)[2]

        # -- If we're given transforms we need to convert them to
        # -- vectors
        if isinstance(point_a, str):
            point_a = mc.xform(
                point_a,
                query=True,
                translation=True,
                worldSpace=True,
            )

        if isinstance(point_b, str):
            point_b = mc.xform(
                point_b,
                query=True,
                translation=True,
                worldSpace=True,
            )

        if isinstance(point_c, str):
            point_c = mc.xform(
                point_c,
                query=True,
                translation=True,
                worldSpace=True,
            )

        point_a = om.MVector(*point_a)
        point_b = om.MVector(*point_b)
        point_c = om.MVector(*point_c)

        # -- Create the vectors between the points
        ab = point_b - point_a
        ac = point_c - point_a
        cb = point_c - point_b

        # -- Get the center point between the end points
        center = point_a + (((ab * ac) / (ac * ac))) * ac

        # -- Create a normal vector pointing at the mid point
        normal = (point_b - center).normal()

        # -- Define the length for the upvector
        vector_length = (ab.length() + cb.length()) * length

        # -- Calculate the final vector position
        result = point_b + (vector_length * normal)

        if create:
            node = mc.createNode('transform')
            mc.xform(
                node,
                t=[
                    result.x,
                    result.y,
                    result.z,
                ],
                worldSpace=True,
            )
            mc.select(node)

        return result