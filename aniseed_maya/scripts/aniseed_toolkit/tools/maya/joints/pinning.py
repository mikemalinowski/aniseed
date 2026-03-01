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
        return aniseed_toolkit.pinning.pin(joints or mc.ls(selection=True))


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
        return aniseed_toolkit.pinning.get_pinned_nodes(item or mc.ls(selection=True)[0])


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
        return aniseed_toolkit.pinning.get_pin(item or mc.ls(selection=True)[0])


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
        return aniseed_toolkit.pinning.remove_pins(items or mc.ls(selection=True))


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
        return aniseed_toolkit.pinning.remove_all_pins()


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
        return aniseed_toolkit.pinning.pin_hierarchy(root or mc.ls(selection=True)[0])