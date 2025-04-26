import aniseed_toolkit
import maya.cmds as mc


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
        cns = mc.pointConstraint(
            to_this,
            node,
            maintainOffset=False,
        )[0]

        mc.pointConstraint(
            from_this,
            node,
            maintainOffset=False,
        )

        mc.setAttr(
            cns + "." + mc.pointConstraint(
                cns,
                query=True,
                weightAliasList=True,
            )[0],
            1 - factor
        )

        mc.setAttr(
            cns + "." + mc.pointConstraint(
                cns,
                query=True,
                weightAliasList=True,
            )[-1],
            factor,
        )

        xform = mc.xform(
            node,
            query=True,
            matrix=True,
        )

        mc.delete(cns)

        mc.xform(
            node,
            matrix=xform,
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
        parent_buffer = mc.createNode("transform")
        child_buffer = mc.createNode("transform")

        mc.parent(
            child_buffer,
            parent_buffer,
        )

        mc.xform(
            parent_buffer,
            matrix=mc.xform(
                relative_to,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
        )

        mc.xform(
            child_buffer,
            matrix=mc.xform(
                node,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        relative_matrix = mc.xform(
            child_buffer,
            query=True,
            matrix=True,
        )

        mc.delete(parent_buffer)

        return relative_matrix


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
        parent_buffer = mc.createNode("transform")
        child_buffer = mc.createNode("transform")

        mc.parent(
            child_buffer,
            parent_buffer,
        )

        mc.xform(
            parent_buffer,
            matrix=mc.xform(
                relative_to,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
        )

        mc.xform(
            child_buffer,
            matrix=matrix,
        )

        mc.xform(
            node,
            matrix=mc.xform(
                child_buffer,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        mc.delete(parent_buffer)
