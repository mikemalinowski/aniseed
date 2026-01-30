import typing
import qtility
import aniseed_toolkit
import maya.cmds as mc
import maya.api.OpenMaya as om


class CombineShapes(aniseed_toolkit.Tool):

    identifier = 'Combine Shapes'
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    # --------------------------------------------------------------------------------------
    def run(self, nodes: typing.List[str] = None):
        """
        Parents all the shapes under all the given nodes under the first given node

        Args:
            nodes: List of nodes to combine, with the first one being the node where
                all the resulting shapes will be applied

        Returns:
            None
        """
        if not nodes:
            nodes = mc.ls(sl=True)

        if not nodes:
            return

        if len(nodes) < 2:
            print("At least two nodes must be given")
            return

        base_node = nodes[0]

        for node in nodes[1:]:

            for shape in mc.listRelatives(node, type="nurbsCurve"):
                mc.parent(
                    shape,
                    base_node,
                    shape=True,
                    r=True,
                )

            mc.delete(node)


class RotateShapes(aniseed_toolkit.Tool):

    identifier = 'Rotate Shapes'
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(
        self,
        node: str = "",
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        pivot: list[float] or str = None,
    ) -> None:
        """
        Spins the shape around by the given x, y, z (local values)

        Args:
            node: The node whose shapes should be spun
            x: Amount to spin on the shapes local X axis in degrees
            y: Amount to spin on the shapes local Y axis in degrees
            z: Amount to spin on the shapes local Z axis in degrees
            pivot: Optional alternate pivot to rotate around. This can
                either be a vector (list[float]) or an actual object (str)

        Returns:
            None
        """
        if not node:
            node = mc.ls(sl=True)[0]

        # -- If we"re not given a pivot, then default
        # -- to a zero vector.
        pivot = pivot or list()

        # -- Get a list of all the curves we need to modify
        all_curves = list()

        if mc.nodeType(node) == "transform" or mc.nodeType(node) == "joint":
            all_curves.extend(
                mc.listRelatives(
                    node,
                    shapes=True,
                )
            )

        elif mc.nodeType(node) == "nurbsCurve":
            all_curves.append(node)

        # -- Validate that all entries are nurbs curves
        all_curves = [
            curve
            for curve in all_curves
            if mc.nodeType(curve) == "nurbsCurve"
        ]

        for curve in all_curves:

            dag = aniseed_toolkit.run("Get DagPath", curve)
            nurbs_fn = om.MFnNurbsCurve(dag)

            for idx in range(nurbs_fn.numCVs):
                worldspace_cv = nurbs_fn.cvPosition(idx, om.MSpace.kObject)

                worldspace_vector = om.MVector(worldspace_cv)
                # -- Get the relative vector between the cv and pivot
                relative_cv = worldspace_vector #- pivot

                # -- Rotate our relative vector by the rotation values
                # -- given to us
                rotated_position = relative_cv.rotateBy(
                    om.MEulerRotation(x * 0.017453, y * 0.017453, z * 0.017453),
                )

                # -- Add the worldspace pivot vector onto our rotated vector
                # -- to give ourselves the final vector
                final_position = rotated_position# + pivot

                nurbs_fn.setCVPosition(
                    idx,
                    om.MPoint(
                        final_position.x,
                        final_position.y,
                        final_position.z,
                    ),
                    space=om.MSpace.kObject,
                )

            nurbs_fn.updateCurve()


class OffsetShapes(aniseed_toolkit.Tool):

    identifier = "Offset Shapes"
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    # noinspection PyUnresolvedReferences
    def run(
        self,
        node: str = "",
        offset_by: float = 0,
        x: float = 1.0,
        y: float = 1.0,
        z: float = 1.0,
    ) -> None:
        """
        This will do an in-place scaling of the shapes for a given node

        Args:
            node: The node whose shapes should be offset
            offset_by: The amount to offset the shapes by
            x: A multiplier for the offset amount specifically on the x axis
            y: A multiplier for the offset amount specifically on the y axis
            z: A multiplier for the offset amount specifically on the z axis

        Returns:
            None
        """

        if not node:
            node = mc.ls(sl=True)[0]

        curves = mc.listRelatives(node, type="nurbsCurve")

        if not curves:
            return

        for curve in curves:
            mc.xform(
                f"{curve}.cv[:]",
                translation=[
                    offset_by * x,
                    offset_by * y,
                    offset_by * z,
                ],
                relative=True,
            )


class ScaleShapes(aniseed_toolkit.Tool):

    identifier = "Scale Shapes"
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(
        self,
        node: str = "",
        scale_by: float = 1,
        x: float = 1.0,
        y:float = 1.0,
        z: float = 1.0,
    ) -> None:
        """
        This will do an in-place scaling of the shapes for a given node

        Args:
            node: The node whose shapes should be offset
            scale_by: The amount to offset the shapes by
            x: A multiplier for the offset amount specifically on the x axis
            y: A multiplier for the offset amount specifically on the y axis
            z: A multiplier for the offset amount specifically on the z axis

        Returns:
            None
        """
        if not node:
            node = mc.ls(sl=True)[0]

        if mc.nodeType(node) == "nurbsCurve":
            curves = [node]
        else:
            curves = mc.listRelatives(node, type="nurbsCurve")

        if not curves:
            return

        for curve in curves:
            mc.xform(
                f"{curve}.cv[:]",
                scale=[
                    scale_by * x,
                    scale_by * y,
                    scale_by * z,
                ],
            )


class RotateShapeFromUpAxis(aniseed_toolkit.Tool):

    identifier = 'Rotate Shape From Up Axis'
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(self, node: str = "", up_axis: str ="y") -> None:
        """
        Shapes are authored in a Y up environment. If you want to get a rotation vector
        to rotate the shape around based on another axis being up, you can use this
        function to get that vector

        Args:
            node: The node to rotate the shape for
            up_axis: What axis should be considered up
        """

        if not node:
            node = mc.ls(sl=True)[0]

        if not up_axis:
            up_axis = qtility.request.item(
                items=["x", "y", "z"],
                title="Select Up Axis",
                message="Select Up Axis.",
                editable=False,
            )

        if not up_axis:
            return

        vector = [0, 0, 0]
        if up_axis.lower() == "x":
            vector = [0, 0, -90]

        if up_axis.lower() == "z":
            vector = [-90, 0, 0]

        aniseed_toolkit.run(
            "Rotate Shapes",
            node,
            *aniseed_toolkit.run("Get Up Axis Shape Rotation Vector"),
        )


class GetUpAxisShapeRotation(aniseed_toolkit.Tool):

    identifier = "Get Up Axis Shape Rotation Vector"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Shapes",
    ]

    def run(self, up_axis: str = "") -> list[float]:
        """
        Shapes are authored in a Y up environment. If you want to get a rotation vector
        to rotate the shape around based on another axis being up, you can use this
        function to get that vector

        Args:
            up_axis: The axis to be considered up

        Returns:
            List[float] of the rotation to apply to a shape
        """

        if not up_axis:
            up_axis = qtility.request.item(
                items=["x", "y", "z"],
                title="Select Up Axis",
                message="Select Up Axis.",
                editable=False,
            )

        if not up_axis:
            return [0, 0, 0]

        vector = [0, 0, 0]
        if up_axis.lower() == "x":
            vector = [0, 0, -90]

        if up_axis.lower() == "z":
            vector = [-90, 0, 0]


class SnapShapeToNodeTransform(aniseed_toolkit.Tool):

    identifier = "Snap Shape To Node Transform"
    classification = "Rigging"
    categories = [
        "Shapes",
    ]

    def run(self, node_to_snap: str = "", target: str = "") -> list[float]:
        pass

