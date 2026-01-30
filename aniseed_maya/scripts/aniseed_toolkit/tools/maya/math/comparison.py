import aniseed
import aniseed_toolkit
import maya.cmds as mc
from maya.api import OpenMaya as om



class DistanceBetweenTool(aniseed_toolkit.Tool):

    identifier = "Distance Between"
    classification = "Rigging"
    categories = [
        "Math",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["node_a", "node_b"]:
            return aniseed.widgets.ObjectSelector()

    def run(
        self,
        node_a: str = "",
        node_b: str = "",
        print_result: bool = True,
    ) -> float:
        """
        Returns the distance between two objects

        Args:
            node_a: The object to measure from
            node_b: The object to measure to
            print_result: If true, the result will be printed

        Returns:
            The distance between two objects
        """

        if not node_a:
            node_a = mc.ls(sl=True)[0]

        if not node_b:
            node_b = mc.ls(sl=True)[1]

        point_a = mc.xform(
            node_a,
            query=True,
            translation=True,
            worldSpace=True,
        )

        point_b = mc.xform(
            node_b,
            query=True,
            translation=True,
            worldSpace=True,
        )

        point_a = om.MVector(*point_a)
        point_b = om.MVector(*point_b)

        delta = point_b - point_a

        print(f"Distance between {node_a} and {node_b} is {delta}")
        return delta.length()


class FactorBetween(aniseed_toolkit.Tool):

    identifier = "Get Factor Between"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Math",
    ]

    def run(self, node: str = "", from_this: str = "", to_this: str = "") -> float:
        """
        This will return a factor (between zero and one) for how close the given
        node is between the from_this and to_this nodes.

        Args:
            node: The node to monitor
            from_this: The first node to compare to
            to_this: The second node to compare to

        Returns:
            The factor for how close the given node is between the from_this and to_this
        """
        total_distance = aniseed_toolkit.run(
            "Distance Between",
            from_this,
            to_this,
        )

        delta = aniseed_toolkit.run(
            "Distance Between",
            node,
            to_this,
        )

        distance_factor = max(
            0.0,
            min(
                1.0,
                delta / total_distance,
            ),
        )

        return distance_factor


class DirectionBetween(aniseed_toolkit.Tool):

    identifier = "Direction Between"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Math",
    ]

    def run(
        self,
        node_a: str = "",
        node_b: str = "",
        print_result: bool = True,
    ) -> list[float]:
        """
        This will return a direction vector (normalised vector) between the
        two nodes

        Args:
            node_a: The object to measure from
            node_b: The object to measure to
            print_result: If true, the result will be printed

        Returns:
            The direction vector between the two nodes
        """
        a = mc.rename(mc.createNode("transform"), "Xfoo1")
        b = mc.rename(mc.createNode("transform"), "Xfoo2")

        mc.parent(
            b,
            a,
        )

        mc.xform(
            a,
            matrix=mc.xform(
                node_a,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        mc.xform(
            b,
            matrix=mc.xform(
                node_b,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        tx = mc.xform(
            b,
            query=True,
            translation=True,
        )

        n = om.MVector(*tx).normal()

        mc.delete(a)

        if print_result:
            print(f"Direction between {node_a} and {node_b} is {n}")

        return n
