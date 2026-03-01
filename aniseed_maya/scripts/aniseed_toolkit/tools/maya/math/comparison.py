import aniseed
import aniseed_toolkit


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
        return aniseed_toolkit.transformation.distance_between(
            node_a=node_a,
            node_b=node_b,
            print_result=True,
        )


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
        return aniseed_toolkit.transformation.factor_between(
            node=node,
            from_this=from_this,
            to_this=to_this,
            print_result=True,
        )


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
        return aniseed_toolkit.transformation.direction_between(
            node_a=node_a,
            node_b=node_b,
            print_result=True,
        )
