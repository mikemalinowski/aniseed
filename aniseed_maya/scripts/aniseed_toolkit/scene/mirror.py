"""
Mirroring transforms across a plane, optionally swapping names to find the
opposite node.
"""
import collections

from maya import cmds

from . import joints as _joints


MIRROR_PLANES = {
    "Z": 'XY',
    "X": 'YZ',
    "Y": 'XZ',
}


def mirror_transforms(
    transforms: list[str] or str = None,
    across: str = "YZ",
    behaviour: bool = True,
    rotate_flip: bool = False,
    name_replacement: list = None,
):
    """
    This function is taken from github with a minor modification. The
    author and credit goes to Andreas Ranman.

    Github Url:
        https://gist.github.com/rondreas/1c6d4e5fc6535649780d5b65fc5a9283

    Mirrors transform across hyperplane.

    Args:
        transforms: list of Transform or string.
        across: plane which to mirror across (XY, YX or XZ).
        behaviour: If true, it should mirror the rotational behaviour too
        rotate_flip: If true, the result is flipped 180 degrees in X and Y
        name_replacement : a tuple of length two, where the first part should
            be replaced with the second part. If None, each transform's
            mirrored matrix is applied to the transform itself.

    Note: this never prompts the user - see ui.dialogs.global_mirror for the
    interactive version.
    """
    # No specified transforms, so will get selection
    if not transforms:
        transforms = cmds.ls(selection=True)


    # Validate plane which to mirror across,
    if across not in ('XY', 'YZ', 'XZ'):
        raise ValueError(
            "Keyword Argument: 'across' not of accepted value ('XY', 'YZ', 'XZ').")


    stored_matrices = collections.OrderedDict()

    for transform in transforms:

        node_type = cmds.nodeType(transform)

        allowable_types = [
            "transform",
            "joint",
        ]

        if node_type not in allowable_types:
            print(f"{transform} is not a transform or joint, skipping")
            continue

        # Get the worldspace matrix, as a list of 16 float values
        mtx = cmds.xform(transform, query=True, worldSpace=True, matrix=True)

        # Invert rotation columns,
        rx = [n * -1 for n in mtx[0:9:4]]
        ry = [n * -1 for n in mtx[1:10:4]]
        rz = [n * -1 for n in mtx[2:11:4]]

        # Invert translation row,
        t = [n * -1 for n in mtx[12:15]]

        # Set matrix based on given plane, and whether to include behaviour or not.
        if str(across) == 'XY':
            mtx[14] = t[2]  # set inverse of the Z translation

            # Set inverse of all rotation columns but for the one we've set translate to.
            if behaviour:
                mtx[0:9:4] = rx
                mtx[1:10:4] = ry

        elif str(across) == 'YZ':
            mtx[12] = t[0]  # set inverse of the X translation

            if behaviour:
                mtx[1:10:4] = ry
                mtx[2:11:4] = rz
        else:
            mtx[13] = t[1]  # set inverse of the Y translation

            if behaviour:
                mtx[0:9:4] = rx
                mtx[2:11:4] = rz

        stored_matrices[transform] = mtx

    for _ in stored_matrices:
        for transform in stored_matrices:
            target = transform

            if name_replacement:
                target = target.replace(
                    name_replacement[0],
                    name_replacement[1],
                )

            cmds.xform(
                target,
                worldSpace=True,
                matrix=stored_matrices[transform]
            )

            if rotate_flip:
                cmds.select(clear=True)
                joint = cmds.joint()
                cmds.xform(joint, matrix=stored_matrices[transform])

                _joints.move_rotations_to_orients([joint])
                cmds.setAttr(f"{joint}.rotateY", 180)
                cmds.setAttr(f"{joint}.rotateX", 180)
                _joints.move_orients_to_rotation([joint])
                cmds.xform(target, matrix=cmds.xform(joint, q=True, m=True, ws=True), ws=True)
                cmds.delete(joint)


def invert_translation(transforms: list[str] = None) -> None:
    """
    This will invert the translation channels of a node

    Args:
        transforms: List of transforms to invert the translation of

    Returns:
        None
    """
    if not transforms:
        transforms = cmds.ls(selection=True, type="joint")

    parent_map = dict()

    for transform in transforms:
        for axis in ["tx", "ty", "tz"]:

            cmds.setAttr(
                f"{transform}.{axis}",
                cmds.getAttr(f"{transform}.{axis}") * -1,
            )
