"""
Pins: world space controls which hold joints in place so they can be
manipulated without affecting their children.

A pin is a PIN_<joint> transform (with a PINOFFSET_<joint> child) whose
pin_link attribute is connected from the joint's message attribute. The
offset parent and scale constrains the joint.

Note: the queries return node names exactly as maya reports them, so they
use cmds rather than mref.
"""
from maya import cmds
import mref

from ..registry import tool
from ..core._nodes import resolve as _resolve
from ..scene import shapes as _shapes



def pin(joints: list[str] = None) -> list[str]:
    """
    This will create a pin for the given joints. Pins are used to
    lock the transforms of a joint to a controller which is typically
    in worldspace. This makes it easy to manipulate joints without altering
    their children.

    The pin shapes are sized by the joint radius (or 1 if the node has no
    radius) and coloured red, and the joint's local axis is displayed. The
    last pin created is left selected.

    Args:
        joints: List of joints to pin. This must be given (None raises an
            error).

    Returns:
        List of created pins.
    """
    pins = []

    for joint in joints:

        pin_node = mref.create("transform")
        pin_node.rename(f"PIN_{joint}")

        pin_node.add_attribute(
            "is_pin",
            value=None,
            attribute_type="bool",
            defaultValue=True,
        )

        pin_link = pin_node.add_attribute(
            "pin_link",
            value=None,
            attribute_type="message",
        )

        pin_offset = mref.create("transform")
        pin_offset.rename(f"PINOFFSET_{joint}")

        # -- Both are new transforms at the origin, so set_parent's
        # -- absolute parenting is identical to a plain cmds.parent
        pin_offset.set_parent(pin_node)

        try:
            radius = mref.getAttr(f"{joint}.radius")
        except Exception:
            radius = 1

        # -- The pin shows as a pin shape, with a sphere for the offset
        _shapes.load_shape(pin_node.name(), "core_pin")
        _shapes.scale(pin_node.name(), scale_by=radius * 8)

        _shapes.load_shape(pin_offset.name(), "core_sphere")
        _shapes.scale(pin_offset.name(), scale_by=radius * 3)

        # -- Colours are given in the 0-255 range
        for node in [pin_node, pin_offset]:
            _shapes.apply_color(node.name(), r=255, g=0, b=0)

        pin_node.match_to(_resolve(joint))

        # -- The passthrough (rather than Attribute.connect) is used so
        # -- that a failed connection raises
        mref.connectAttr(
            f"{joint}.message",
            pin_link,
        )

        mref.parentConstraint(
            pin_offset,
            joint,
            maintainOffset=False,
        )

        mref.scaleConstraint(
            pin_offset,
            joint,
            maintainOffset=False,
        )

        try:
            mref.setAttr(
                f"{joint}.displayLocalAxis",
                True,
            )
        except Exception:
            pass

        pin_node.select()
        pins.append(pin_node.name())

    return pins


def get_pinned_nodes(item: str = "") -> str or None:
    """
    This will attempt to find the joint from a pin setup. The item can be
    the pin or its offset.

    Args:
        item: The node to inspect

    Returns:
        The joint being pinned (or None if no joint was found). An error
        is raised if the item has no pin_link attribute (such as a joint).
    """
    if item.startswith("PINOFFSET_"):
        item = cmds.listRelatives(item, parent=True)[0]

    connections = cmds.listConnections(f"{item}.pin_link") or list()
    return connections[0] if connections else None


def get_pin(item: str = "") -> str or None:
    """
    This will return the pin control for the given node. If the pin control
    was the item given it will just be returned.

    Args:
        item: The pin, the pin offset or a pinned joint

    Returns:
        The pin control, or None if no pin was found
    """

    if item.startswith("PIN_"):
        return item

    if item.startswith("PINOFFSET_"):
        return cmds.listRelatives(item, parent=True)[0]

    for connection in cmds.listConnections(f"{item}.message") or list():
        if connection.startswith("PIN_"):
            return connection

    return None


def is_pinned(item: str = None) -> bool:
    """
    This will test whether the given item is already pinned or not.

    Args:
        item: The item to test. If not given, the first selected node is
            used.

    Returns:
        True if the item is pinned
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
    in the given list. Each pinned joint keeps the local transform it had
    before its pin was removed, and its local axis display is turned off.

    Args:
        items: List of pins, pin offsets or pinned joints to remove the pins
            for. This must be given (None raises an error).

    Returns:
        None
    """
    for pin_or_joint in items:

        joint = get_pinned_nodes(pin_or_joint)
        pin = get_pin(pin_or_joint)

        # -- cmds is used deliberately here: if no joint/pin is found the
        # -- name is None, and cmds then acts on the selection.
        pre_xform = cmds.xform(
            joint,
            matrix=True,
            query=True,
        )

        try:
            cmds.setAttr(
                f"{joint}.displayLocalAxis",
                False,
            )
        except Exception:
            pass

        cmds.delete(pin)

        cmds.xform(
            joint,
            matrix=pre_xform,
        )


@tool(
    "Remove All Pins",
    classification="Rigging",
    categories=["Pinning"],
)
def remove_all_pins():
    """
    This will remove all pins in the entire scene
    """
    for pin in cmds.ls("*.pin_link", recursive=True, objectsOnly=True):
        remove_pins([pin])


def pin_hierarchy(root: str = None) -> list[str]:
    """
    This will pin the given joint and all the joints beneath it.

    Args:
        root: The joint to start pinning from. If not given, nothing is
            pinned.

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
