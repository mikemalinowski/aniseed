import maya.cmds as mc

from . import hierarchy
from . import constants as c


# ------------------------------------------------------------------------------
def move_rotations_to_joint_orients(joints=None):
    """
    Moves the rotations on the skeleton to the joint orients

    :return: None
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


# ------------------------------------------------------------------------------
def move_joint_orients_to_rotations(joints=None):
    """
    Moves the values from the joint orient of the node to the rotation
    whilst retaining the transform of the node.

    :param joints: The joint to alter
    :type joints: pm.nt.Joint

    :return: None
    """

    if isinstance(joints, str):
        joints = [joints]

    if not joints:
        joints = mc.ls(sl=True)

    if not joints:
        print("no joints given")
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

