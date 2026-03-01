import aniseed_toolkit
import maya.cmds as mc


class HideNodesTool(aniseed_toolkit.Tool):

    identifier = "Hide Nodes"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, items: list[str] = None) -> None:
        """
        This will hide all the given nodes. However, it will first do a
        node type test, and if it is a joint it will hide it using the joint
        style attribute rather than the visibility attribute.

        Args:
            items: List of nodes to hide

        Returns:
            None
        """
        aniseed_toolkit.visibility.hide(items)


class ShowNodesTool(aniseed_toolkit.Tool):

    identifier = "Show Nodes"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, items: list[str] = None) -> None:
        """
        This will show all the given nodes. However, it will first do a
        node type test, and if it is a joint it will show it using the joint
        style attribute rather than the visibility attribute.

        Args:
            items: List of nodes to hide

        Returns:
            None
        """
        aniseed_toolkit.visibility.show(items)
