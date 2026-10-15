import aniseed_toolkit
import maya.cmds as mc


class IsPinnedTool(aniseed_toolkit.Tool):

    identifier = "Is Pinned"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Pinning",
    ]

    def run(self, joint: str = None) -> bool:
        """
        This will test whether the given item is already pinned or not.

        Args:
            joint: The item to test

        Returns:
            True if the joint is pinned
        """
        return aniseed_toolkit.pinning.is_pinned(joint or mc.ls(selection=True)[0])


@aniseed_toolkit.tool(
    "Create Pins",
    classification="Rigging",
    categories=["Pinning"],
)
def create_pins(joints: list[str] = None) -> list[str]:
    """
    This will create a pin for the given joints. Pins are used to
    lock the transforms of a joint to a controller which is typically
    in worldspace. This makes it easy to manipulate joints without altering
    their children.

    Args:
        joints: List of joints to pin

    Returns:
        List of created pins.
    """
    return aniseed_toolkit.rig.pinning.pin(joints or mc.ls(selection=True))


@aniseed_toolkit.tool(
    "Get Joint From Pin",
    classification="Rigging",
    categories=["Pinning"],
    user_facing=False,
)
def get_joint_from_pin(item: str = "") -> str or None:
    """
    This will attempt to find the joint from a pin setup. If the joint
    itself is given, the same joint will be returned.

    Args:
        item: The node to inspect

    Returns:
        The joint being pinned (or None if no joint was found)
    """
    return aniseed_toolkit.rig.pinning.get_pinned_nodes(item or mc.ls(selection=True)[0])


@aniseed_toolkit.tool(
    "Get Pin From Node",
    classification="Rigging",
    categories=["Pinning"],
    user_facing=False,
)
def get_pin_from_node(item: str = "") -> str or None:
    """
    This will return the pin control for the given node. If the pin control
    was the item given it will just be returned.

    Args:
        item: The item to find the pin for

    Returns:
        The pin control
    """
    return aniseed_toolkit.rig.pinning.get_pin(item or mc.ls(selection=True)[0])


@aniseed_toolkit.tool(
    "Pin Hierarchy",
    classification="Rigging",
    categories=["Pinning"],
)
def pin_hierarchy(root: str = None) -> list[str]:
    """
    This will pin all joints in the entire hierarchy
    starting from the given root.

    Args:
        root: The joint to start pinning from

    Returns:
        List of created pin controls
    """
    return aniseed_toolkit.rig.pinning.pin_hierarchy(root or mc.ls(selection=True)[0])


@aniseed_toolkit.tool(
    "Remove Pins",
    classification="Rigging",
    categories=["Pinning"],
)
def remove_pins(items: list[str] = None) -> None:
    """
    This will remove any pins which are pinning any of the nodes
    in the given list.

    Args:
        items: List of nodes to remove pins for

    Returns:
        None
    """
    return aniseed_toolkit.rig.pinning.remove_pins(items or mc.ls(selection=True))
