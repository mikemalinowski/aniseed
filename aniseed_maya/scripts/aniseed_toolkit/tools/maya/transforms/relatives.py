import aniseed_toolkit
import maya.cmds as mc
import maya.api.OpenMaya as om


class PositionBetweenTool(aniseed_toolkit.Tool):

    identifier = "Position Between"
    categories = [
        "Transforms",
    ]

    def run(
        self,
        node: str = "",
        from_this: str = "",
        to_this: str = "",
        factor = 0.5,
    ):
        """
        This will set the translation of the given node to be at a position
        between from_this and to_this based on the factor value. A factor
        of zero will mean a position on top of from_this, whilst a factor
        of 1 will mean a position on bottom of to_this.

        Args:
            node: The node to adjust the position for
            from_this: The first node to consider
            to_this: The second node to consider
            factor: The factor value to use

        Returns:
            None
        """
        return aniseed_toolkit.transformation.position_between(
            node=node,
            from_this=from_this,
            to_this=to_this,
            factor=factor,
        )


class GetRelativeMatrixTool(aniseed_toolkit.Tool):

    identifier = "Get Relative Matrix"
    user_facing = False
    categories = [
        "Transforms",
    ]

    def run(self, node: str = "", relative_to: str = "") -> list[float]:
        """
        This will get a matrix which is the relative matrix between the relative_to
        and the node item

        Args:
            node: The node to consider as the child
            relative_to: The node to consider as the parent

        Returns:
            relative matrix as a list (maya.cmds)
        """
        return aniseed_toolkit.transformation.get_relative_matrix(
            node=node,
            relative_to=relative_to,
        )


class ApplyRelativeMatrixTool(aniseed_toolkit.Tool):

    identifier = "Apply Relative Matrix"
    user_facing = False
    categories = [
        "Transforms",
    ]

    def run(self, node: str, matrix: list[float], relative_to: str = ""):
        """
        This will apply the matrix to the node as if the node were a child
        of the relative_to node

        Args:
            node: The node to adjust
            matrix: The matrix to apply (maya.cmds)
            relative_to: The node to use as a parent for spatial transforms

        Returns:
            None
        """
        return aniseed_toolkit.transformation.apply_relative_matrix(
            node=node,
            matrix=matrix,
            relative_to=relative_to,
        )
