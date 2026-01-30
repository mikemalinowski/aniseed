import aniseed_toolkit
import maya.cmds as mc


class CreatePinsTool(aniseed_toolkit.Tool):

    identifier = "Create Pins"
    classification = "Rigging"
    categories = [
        "Pinning",
    ]

    def run(self, joints: list[str] = None) -> list[str]:
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
        if not joints:
            joints = mc.ls(sl=True)

        pins = []

        for joint in joints:

            if mc.nodeType(joint) != "joint":
                continue

            pin_node = mc.rename(
                mc.createNode("transform"),
                f"PIN_{joint}",
            )

            mc.addAttr(
                pin_node,
                shortName="is_pin",
                at="bool",
                dv=True,
            )

            mc.addAttr(
                pin_node,
                shortName="pin_link",
                at="message",
            )

            pin_offset = mc.rename(
                mc.createNode("transform"),
                f"PINOFFSET_{joint}",
            )

            mc.parent(
                pin_offset,
                pin_node,
            )

            aniseed_toolkit.run(
                "Apply Shape",
                pin_node,
                "core_pin",
            )

            aniseed_toolkit.run(
                "Scale Shapes",
                pin_node,
                mc.getAttr(f"{joint}.radius") * 8,
            )

            aniseed_toolkit.run(
                "Apply Shape",
                pin_offset,
                "core_sphere",
            )

            aniseed_toolkit.run(
                "Scale Shapes",
                pin_offset,
                mc.getAttr(f"{joint}.radius") * 3,
            )

            for node in [pin_node, pin_offset]:
                aniseed_toolkit.run("Apply Shape Color", node, r=1, g=0, b=0)

            mc.xform(
                pin_node,
                matrix=mc.xform(
                    joint,
                    query=True,
                    worldSpace=True,
                    matrix=True,
                ),
                worldSpace=True,
            )

            mc.connectAttr(
                f"{joint}.message",
                f"{pin_node}.pin_link",
            )

            mc.parentConstraint(
                pin_offset,
                joint,
                maintainOffset=False,
            )

            mc.scaleConstraint(
                pin_offset,
                joint,
                maintainOffset=False,
            )

            mc.setAttr(
                f"{joint}.displayLocalAxis",
                True,
            )

            mc.select(pin_node)
            pins.append(pin_node)

        return pins


class GetJointFromPinTool(aniseed_toolkit.Tool):

    identifier = "Get Joint From Pin"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Pinning",
    ]
    def run(self, item: str = "") -> str or None:
        """
        This will attempt to find the joint from a pin setup. If the joint
        itself is given, the same joint will be returned.

        Args:
            item: The node to inspect

        Returns:
            The joint being pinned (or None if no joint was found)
        """
        if mc.nodeType(item) == "joint":
            return item

        if item.startswith("PINOFFSET_"):
            item = mc.listRelatives(item, parent=True)[0]

        for potential_result in mc.listConnections(f"{item}.pin_link") or list():
            if mc.nodeType(potential_result) == "joint":
                return potential_result

        return None


class GetPinFromNode(aniseed_toolkit.Tool):

    identifier = "Get Pin From Node"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Pinning",
    ]

    def run(self, item: str = "") -> str or None:
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

        if mc.nodeType(item) == "joint":
            for item in mc.listConnections(f"{item}.message") or list():
                if item.startswith("PIN_"):
                    return item

        if item.startswith("PINOFFSET_"):
            return mc.listRelatives(item, parent=True)[0]

        return None


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
        if not joint:
            joint = mc.ls(sl=True)[0]

        for item in mc.listConnections(f"{joint}.message") or list():
            if item.startswith("PIN_"):
                return True

        return False


class RemovePinTool(aniseed_toolkit.Tool):

    identifier = "Remove Pins"
    classification = "Rigging"
    categories = [
        "Pinning",
    ]

    def run(self, items: list[str] = None) -> None:
        """
        This will remove any pins which are pinning any of the nodes
        in the given list.

        Args:
            items: List of nodes to remove pins for

        Returns:
            None
        """
        if not items:
            items = mc.ls(sl=True)

        for pin_or_joint in items:

            joint = aniseed_toolkit.run("Get Joint From Pin", pin_or_joint)
            pin = aniseed_toolkit.run("Get Pin From Node",pin_or_joint)

            pre_xform = mc.xform(
                joint,
                matrix=True,
                query=True,
            )

            mc.setAttr(
                f"{joint}.displayLocalAxis",
                False,
            )

            mc.delete(pin)

            mc.xform(
                joint,
                matrix=pre_xform,
            )


class RemoveAllPinsTool(aniseed_toolkit.Tool):

    identifier = "Remove All Pins"
    classification = "Rigging"
    categories = [
        "Pinning",
    ]

    def run(self):
        """
        This will remove all pins in the entire scene
        """
        for pin in mc.ls("*.pin_link", r=True, o=True):
            aniseed_toolkit.run("Remove Pins", [pin])


class PinHierarchy(aniseed_toolkit.Tool):

    identifier = "Pin Hierarchy"
    classification = "Rigging"
    categories = [
        "Pinning",
    ]

    def run(self, root: str = None) -> list[str]:
        """
        This will pin all joints in the entire hierarchy
        starting from the given root.

        Args:
            root: The joint to start pinning from

        Returns:
            List of created pin controls
        """
        if not root:
            root = mc.ls(sl=True)[0]

        if not root:
            return []

        nodes = [root]

        nodes.extend(
            mc.listRelatives(
                root,
                allDescendents=True,
                type="joint",
            ),
        )

        return aniseed_toolkit.run("Create Pins", nodes)
