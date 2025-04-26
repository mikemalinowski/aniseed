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
        if not items:
            items = mc.ls(sl=True)

        if not isinstance(items, list):
            items = [items]

        for item in items:

            if  mc.nodeType(item, "joint"):
                mc.setAttr(
                    f"{item}.drawStyle",
                    2,  # Invisible
                )

            else:
                mc.setAttr(
                    f"{item}.visibility",
                    False,
                )


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
        if not items:
            items = mc.ls(sl=True)

        if not isinstance(items, list):
            items = [items]

        for item in items:

            if mc.nodeType(item, "joint"):
                mc.setAttr(
                    f"{item}.drawStyle",
                    0,  # Bone
                )

            else:
                mc.setAttr(
                    f"{item}.visibility",
                    True,
                )
