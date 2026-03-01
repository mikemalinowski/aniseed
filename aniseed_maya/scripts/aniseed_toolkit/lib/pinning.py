import aniseed_toolkit
from maya import cmds


def pin(joints: list[str] = None) -> list[str]:
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
    pins = []

    for joint in joints:

        pin_node = cmds.rename(
            cmds.createNode("transform"),
            f"PIN_{joint}",
        )

        cmds.addAttr(
            pin_node,
            shortName="is_pin",
            attributeType="bool",
            defaultValue=True,
        )

        cmds.addAttr(
            pin_node,
            shortName="pin_link",
            attributeType="message",
        )

        pin_offset = cmds.rename(
            cmds.createNode("transform"),
            f"PINOFFSET_{joint}",
        )

        cmds.parent(
            pin_offset,
            pin_node,
        )

        try:
            radius = cmds.getAttr(f"{joint}.radius")
        except:
            radius = 1

        aniseed_toolkit.run(
            "Apply Shape",
            pin_node,
            "core_pin",
        )

        aniseed_toolkit.run(
            "Scale Shapes",
            pin_node,
            radius * 8,
        )

        aniseed_toolkit.run(
            "Apply Shape",
            pin_offset,
            "core_sphere",
        )

        try:
            aniseed_toolkit.run(
                "Scale Shapes",
                pin_offset,
                radius * 3,
            )
        except ValueError:
            pass

        for node in [pin_node, pin_offset]:
            aniseed_toolkit.run("Apply Shape Color", node, r=1, g=0, b=0)

        cmds.xform(
            pin_node,
            matrix=cmds.xform(
                joint,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
            worldSpace=True,
        )

        cmds.connectAttr(
            f"{joint}.message",
            f"{pin_node}.pin_link",
        )

        cmds.parentConstraint(
            pin_offset,
            joint,
            maintainOffset=False,
        )

        cmds.scaleConstraint(
            pin_offset,
            joint,
            maintainOffset=False,
        )

        cmds.setAttr(
            f"{joint}.displayLocalAxis",
            True,
        )

        cmds.select(pin_node)
        pins.append(pin_node)

    return pins


def get_pinned_nodes(item: str = "") -> str or None:
    """
    This will attempt to find the joint from a pin setup. If the joint
    itself is given, the same joint will be returned.

    Args:
        item: The node to inspect

    Returns:
        The joint being pinned (or None if no joint was found)
    """
    if item.startswith("PINOFFSET_"):
        item = cmds.listRelatives(item, parent=True)[0]

    for potential_result in cmds.listConnections(f"{item}.pin_link") or list():
        if cmds.nodeType(potential_result) == "joint":
            return potential_result

    return None


def get_pin(item: str = "") -> str or None:
    """
    This will return the pin control for the given node. If the pin control
    was the item given it will just be returned.

    Args:
        item: The item to find the pin for

    Returns:
        The pin control
    """

    if item.startswith("PIN_"):
        return item

    if cmds.nodeType(item) == "joint":
        for item in cmds.listConnections(f"{item}.message") or list():
            if item.startswith("PIN_"):
                return item

    if item.startswith("PINOFFSET_"):
        return cmds.listRelatives(item, parent=True)[0]

    return None


def is_pinned(item: str = None) -> bool:
    """
    This will test whether the given item is already pinned or not.

    Args:
        joint: The item to test

    Returns:
        True if the joint is pinned
    """
    if not item:
        item = cmds.ls(selection=True)[0]

    for connection in cmds.listConnections(f"{item}.message") or list():
        if connection.startswith("PIN_"):
            return True

    return False


def remove_pins(items: list[str] = None) -> None:
    """
    This will remove any pins which are pinning any of the nodes
    in the given list.

    Args:
        items: List of nodes to remove pins for

    Returns:
        None
    """
    for pin_or_joint in items:

        joint = aniseed_toolkit.run("Get Joint From Pin", pin_or_joint)
        pin = aniseed_toolkit.run("Get Pin From Node",pin_or_joint)

        pre_xform = cmds.xform(
            joint,
            matrix=True,
            query=True,
        )

        cmds.setAttr(
            f"{joint}.displayLocalAxis",
            False,
        )

        cmds.delete(pin)

        cmds.xform(
            joint,
            matrix=pre_xform,
        )


def remove_all_pins():
    """
    This will remove all pins in the entire scene
    """
    for pin in cmds.ls("*.pin_link", recursive=True, objectsOnly=True):
        remove_pins([pin])


def pin_hierarchy(root: str = None) -> list[str]:
    """
    This will pin all joints in the entire hierarchy
    starting from the given root.

    Args:
        root: The joint to start pinning from

    Returns:
        List of created pin controls
    """
    if not root:
        return []

    nodes = [root]

    nodes.extend(
        cmds.listRelatives(
            root,
            allDescendents=True,
            type="joint",
        ),
    )

    return pin(nodes)
