"""
Mirroring transforms across a plane, optionally swapping names to find the
opposite node.

Note on maya.cmds: the nodes given by the caller are addressed by name (and
name replacement works on those strings), so those calls stay on cmds and keep
their error behaviour. mref is used for the temporary joint used by
rotate_flip.
"""
import collections
import logging
import typing

from maya import cmds
import mref

from . import joints as _joints

log = logging.getLogger(__name__)


MIRROR_PLANES = {
    "Z": 'XY',
    "X": 'YZ',
    "Y": 'XZ',
}


def mirror_transforms(
    transforms: typing.Union[list[str], str] = None,
    across: str = "YZ",
    behaviour: bool = True,
    rotate_flip: bool = False,
    name_replacement: list = None,
    targets: list = None,
):
    """
    This function is taken from github with a minor modification. The
    author and credit goes to Andreas Ranman.

    Github Url:
        https://gist.github.com/rondreas/1c6d4e5fc6535649780d5b65fc5a9283

    Mirrors the world space matrix of each transform across a plane through
    the world origin. Nodes which are not transforms or joints are skipped
    (with a warning logged).

    Args:
        transforms: List of transform or joint names. Uses the selection if
            none are given.
        across: Plane which to mirror across ('XY', 'YZ' or 'XZ'). Any other
            value raises a ValueError.
        behaviour: If true, it should mirror the rotational behaviour too
        rotate_flip: If true, the result is flipped 180 degrees in X and Y
        name_replacement: A sequence of two strings; in each transform's
            name the first is replaced with the second to find the node the
            mirrored matrix is applied to. If empty or None, each
            transform's mirrored matrix is applied to the transform itself.
        targets: Optional list of node names, parallel to transforms. When
            given, each transform's mirrored matrix is applied to the target
            at the same index (and name_replacement is ignored). It must be
            the same length as transforms.

    Returns:
        None

    Note: this never prompts the user - see ui.dialogs.global_mirror for the
    interactive version.
    """
    # -- No specified transforms, so use the selection
    if not transforms:
        transforms = cmds.ls(selection=True)

    # -- Validate plane which to mirror across
    if across not in ('XY', 'YZ', 'XZ'):
        raise ValueError(
            "Keyword Argument: 'across' not of accepted value ('XY', 'YZ', 'XZ').")

    if targets is not None and len(targets) != len(transforms):
        raise ValueError("targets must be the same length as transforms")

    # -- Map each transform to the node its mirrored matrix is applied to
    target_lookup = dict(zip(transforms, targets)) if targets is not None else dict()

    stored_matrices = collections.OrderedDict()

    for transform in transforms:

        node_type = cmds.nodeType(transform)

        allowable_types = [
            "transform",
            "joint",
        ]

        if node_type not in allowable_types:
            log.warning(f"{transform} is not a transform or joint, skipping")
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
        if across == 'XY':
            mtx[14] = t[2]  # set inverse of the Z translation

            # Set inverse of all rotation columns but for the one we've set translate to.
            if behaviour:
                mtx[0:9:4] = rx
                mtx[1:10:4] = ry

        elif across == 'YZ':
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

    # -- The matrices are world space, so setting a parent after its child
    # -- moves the child again. Applying the whole set once per transform
    # -- means every node ends up on its mirrored matrix regardless of order.
    for _ in stored_matrices:
        for transform in stored_matrices:
            target = transform

            if targets is not None:
                target = target_lookup[transform]

            elif name_replacement:
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
                # -- Flip using a temporary joint: its rotation is moved to
                # -- its orients, then it is rotated 180 in Y and X and the
                # -- result is applied to the target
                cmds.select(clear=True)
                joint = mref.get(cmds.joint())
                joint.set_matrix(stored_matrices[transform])

                _joints.move_rotations_to_orients([joint.name()])
                joint.attr("rotateY").set(180)
                joint.attr("rotateX").set(180)
                _joints.move_orients_to_rotation([joint.name()])
                cmds.xform(target, matrix=joint.get_matrix(space="world"), ws=True)
                joint.delete()


def invert_translation(transforms: list[str] = None) -> None:
    """
    This will invert (negate) the local translateX/Y/Z values of the given
    nodes.

    Args:
        transforms: List of transforms to invert the translation of. Uses
            the selected joints if none are given.

    Returns:
        None
    """
    if not transforms:
        transforms = cmds.ls(selection=True, type="joint")

    for transform in transforms:
        for axis in ["tx", "ty", "tz"]:

            cmds.setAttr(
                f"{transform}.{axis}",
                cmds.getAttr(f"{transform}.{axis}") * -1,
            )
