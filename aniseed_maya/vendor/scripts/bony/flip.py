import collections
import maya.cmds as mc

from . import utils

# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
@utils.undoable
def global_mirror(
        transforms=None,
        across=None,
        behaviour=True,
        result_remapping=None,
):
    """
    This function is taken from github with a minor modification. The
    author and credit goes to Andreas Ranman.

    Github Url:
        https://gist.github.com/rondreas/1c6d4e5fc6535649780d5b65fc5a9283

    Mirrors transform across hyperplane.

    transforms -- list of Transform or string.
    across -- plane which to mirror across.
    behaviour -- bool
    result_remapping : callable function which can be used to convert the
        name of the given joint to a different target. This is useful when
        you want to mirror the result to an opposite existing object

    """
    # No specified transforms, so will get selection
    if not transforms:
        transforms = mc.ls(sl=True)

    # Validate plane which to mirror across,
    if not across in ('XY', 'YZ', 'XZ'):
        raise ValueError(
            "Keyword Argument: 'across' not of accepted value ('XY', 'YZ', 'XZ').")

    stored_matrices = collections.OrderedDict()

    for transform in transforms:

        node_type = mc.nodeType(transform)

        allowable_types = [
            "transform",
            "joint",
        ]

        if node_type not in allowable_types:
            print(f"{transform} is not a transform or joint, skipping")
            continue

        # Get the worldspace matrix, as a list of 16 float values
        mtx = mc.xform(transform, q=True, ws=True, m=True)

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

    for transform in stored_matrices:
        target = transform

        if result_remapping:
            target = result_remapping(target)

        mc.xform(
            target,
            ws=True,
            m=stored_matrices[transform]
        )



# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
@utils.undoable
def invert(
    transforms=None,
):
    if not transforms:
        transforms = mc.ls(sl=True, type="joint")

    parent_map = dict()

    for transform in transforms:
        for axis in ["tx", "ty", "tz"]:

            mc.setAttr(
                f"{transform}.{axis}",
                mc.getAttr(f"{transform}.{axis}") * -1,
            )
