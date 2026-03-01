import aniseed_toolkit
import maya.cmds as mc


class MoveRotationsToOrients(aniseed_toolkit.Tool):

    identifier = "Move Joint Rotations To Orients"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(self, joints: list[str] = None) -> None:
        """
        Moves the rotations on the given joints to the joint orients
        attributes (zeroing the rotations).

        Args:
            joints: List of joints to move the rotation attributes for

        Returns:
            None
        """
        return aniseed_toolkit.joints.move_rotations_to_orients(joints)


class MoveJointOrientsToRotation(aniseed_toolkit.Tool):

    identifier = "Move Joint Orients to Rotation"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(self, joints: list[str] = None) -> None:
        """
        Moves the values from the joint orient of the node to the rotation
        whilst retaining the transform of the node.

        Args:
            joints: The joint to alter

        Returns:
            None
        """
        return aniseed_toolkit.joints.move_orients_to_rotation(joints)
