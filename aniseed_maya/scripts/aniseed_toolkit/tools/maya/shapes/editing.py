import typing
import aniseed_toolkit
import maya.cmds as mc


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
            nodes = mc.ls(selection=True)

        if not nodes:
            return

        return aniseed_toolkit.shapes.combine(nodes)



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
            node = mc.ls(selection=True)[0]

        return aniseed_toolkit.shapes.rotate(node, x, y, z)


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
            node = mc.ls(selection=True)[0]

        return aniseed_toolkit.shapes.offset(
            node=node,
            offset_by=offset_by,
            x=x,
            y=y,
            z=z,
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
            node = mc.ls(selection=True)[0]

        return aniseed_toolkit.shapes.scale(
            node=node,
            scale_by=scale_by,
            x=x,
            y=y,
            z=z,
        )
