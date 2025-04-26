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
        if isinstance(joints, str):
            joints = [joints]

        if not joints:
            joints = mc.ls(sl=True)

        if not joints:
            return

        for joint in joints:
            # -- Store the world space matrix
            ws_mat4 = mc.xform(
                joint,
                query=True,
                matrix=True,
                worldSpace=True,
            )

            # -- Zero the joint orients
            for attr in ['jointOrientX', 'jointOrientY', 'jointOrientZ']:
                mc.setAttr(
                    f"{joint}.{attr}",
                    0,
                )

            # -- Now we can restore the matrix
            mc.xform(
                joint,
                matrix=ws_mat4,
                worldSpace=True,
            )

            # -- Now we can shift the values from the rotation to the orient
            # -- knowing that the world transform will be retained
            for axis in ['X', 'Y', 'Z']:

                mc.setAttr(
                    f"{joint}.jointOrient{axis}",
                    mc.getAttr(f"{joint}.rotate{axis}"),
                )

                mc.setAttr(
                    f"{joint}.rotate{axis}",
                    0,
                )

        return None


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

        if isinstance(joints, str):
            joints = [joints]

        if not joints:
            joints = mc.ls(sl=True)

        if not joints:
            return

        for joint in joints:
            # -- Store the world space matrix
            ws_mat4 = mc.xform(
                joint,
                query=True,
                matrix=True,
                worldSpace=True,
            )

            # -- Zero the joint orients
            for attr in ['jointOrientX', 'jointOrientY', 'jointOrientZ']:
                mc.setAttr(
                    f"{joint}.{attr}",
                    0,
                )

            # -- Now we can restore the matrix
            mc.xform(
                joint,
                matrix=ws_mat4,
                worldSpace=True,
            )

