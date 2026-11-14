"""
Editing MatrixMixer poses (see matrix_mixer.MatrixMixer) directly on the
objects the mixer drives.

The mixer only writes a driven object's offsetParentMatrix, so its own
channels are free. To edit a pose the user dials the pose in, moves the
driven objects, and calls update_pose. That folds each moved object's local
matrix into the pose, solving for the pose matrix which reproduces it at the
pose's current weight, then zeroes the object's channels. Nothing moves in
world space.

The solve follows the mixer's chain: every pose's rotate/scale part is
multiplied in pose order, then every translation. With the other poses held
where they are, pose k's weighted parts must become

    rotate/scale:  B^-1 * L3 * B * Wk       (B: the poses before k)
    translation:   tL * A + tk              (A: all rotate/scale parts)

where L3 and tL are the moved object's local rotate/scale and translation.
The weighted parts are then un-weighted (the inverse of blendMatrix's
slerp and lerp) to give the full pose matrix.

Mirroring conjugates a pose matrix with the signed axis permutation between
the two objects' rest frames, M' = P^-1 * M * P, which carries rotations and
translations across the reflection without any per-channel rules.
"""
import json
import math
import logging
import contextlib
import dataclasses

import mref
from maya import cmds
from maya.api import OpenMaya as om

from . import matrix_mixer

log = logging.getLogger(__name__)

# -- An edit is divided by the pose weight, so below this (absolute) weight
# -- it would be magnified beyond use and the pose cannot be edited
MINIMUM_WEIGHT = 0.05

# -- Below this (absolute) weight an edit still works, but is noticeably
# -- magnified, so the user is warned
LOW_WEIGHT = 0.5

# -- Every undo chunk opened here starts with this, so a tool can tell when
# -- one of its edits has been undone or redone
UNDO_CHUNK_PREFIX = "MatrixMixerPoseEdit"

# -- Each axis of a driven object's rest frame must line up with an axis of
# -- its mirror's rest frame (once reflected across world X) to at least this
# -- dot product, otherwise the pair is not symmetric enough to mirror
MIRROR_AXIS_ALIGNMENT = 0.95

# -- Shear in an edit above this is reported
SHEAR_TOLERANCE = 1e-4

# -- Name tokens (split on underscores, compared without case) which mark a
# -- side, and the token of the opposite side
SIDE_TOKENS = {
    "left": "right",
    "right": "left",
    "lf": "rt",
    "rt": "lf",
}


def mirror_name(name):
    """
    Returns the name with every side token (see SIDE_TOKENS) swapped for the
    opposite side's, keeping its case: left_brow_up becomes right_brow_up and
    CTL_Brow_LF becomes CTL_Brow_RT. A name without a side token is returned
    unchanged.
    """
    tokens = name.split("_")

    for idx, token in enumerate(tokens):
        opposite = SIDE_TOKENS.get(token.lower())

        if not opposite:
            continue

        if token.isupper():
            opposite = opposite.upper()
        elif token[0].isupper():
            opposite = opposite.capitalize()

        tokens[idx] = opposite

    return "_".join(tokens)


@dataclasses.dataclass
class DrivenLink:
    """
    A driven object of the mixer. When it cannot be edited, problem says why.
    """
    index: int
    key: str
    node: mref.ReferencedItem
    problem: str = ""

    @property
    def editable(self) -> bool:
        return not self.problem


@dataclasses.dataclass
class UpdateResult:
    """
    The outcome of update_pose: the keys of the driven objects baked into
    the pose, the (key, reason) pairs which were skipped and any warnings.
    When mirroring, also the mirror pose and the keys written into it.
    """
    updated: list = dataclasses.field(default_factory=list)
    skipped: list = dataclasses.field(default_factory=list)
    warnings: list = dataclasses.field(default_factory=list)
    mirror_pose: str = ""
    mirrored: list = dataclasses.field(default_factory=list)


@contextlib.contextmanager
def undo_chunk(label):
    """
    Groups everything within the block into a single undo step, named
    UNDO_CHUNK_PREFIX followed by the given label.
    """
    mref.undoInfo(openChunk=True, chunkName=f"{UNDO_CHUNK_PREFIX}: {label}")
    try:
        yield
    finally:
        mref.undoInfo(closeChunk=True)


# --------------------------------------------------------------------------
# -- Driven objects
# --------------------------------------------------------------------------
def resolve_links(mixer) -> list:
    """
    Returns a DrivenLink for every driven object of the mixer, in index
    order, with the reason it cannot be edited where that is the case.
    """
    links = []

    for index, key, node in mixer.driven_entries():
        link = DrivenLink(index=index, key=key, node=node)
        links.append(link)
        name = node.full_name()

        for attribute_name in ("rotateAxis", "jointOrient"):
            if cmds.attributeQuery(attribute_name, node=name, exists=True):
                values = cmds.getAttr(f"{name}.{attribute_name}")[0]

                if any(abs(value) > matrix_mixer.TOLERANCE for value in values):
                    link.problem = f"it has a {attribute_name}, so its channels at rest are not identity"
                    break

    return links


def is_at_rest(node) -> bool:
    """
    Returns True if the node's local matrix (its channels) is identity.
    """
    return matrix_mixer.is_identity(om.MMatrix(cmds.getAttr(f"{mref.get(node).full_name()}.matrix")))


def has_driven_channels(node) -> bool:
    """
    Returns True if any of the node's channels has an input (such as
    animation), which would undo the zeroing.
    """
    name = mref.get(node).full_name()

    for path in matrix_mixer.channel_attributes(node):
        if cmds.listConnections(path, source=True, destination=False):
            return True

    for channel in ("translate", "rotate", "scale"):
        if cmds.listConnections(f"{name}.{channel}", source=True, destination=False):
            return True

    return False


def edited_nodes(links) -> list:
    """
    Returns the editable driven objects which are away from rest, and so
    hold edits which have not been baked into a pose yet.
    """
    return [
        link.node
        for link in links
        if link.editable and not is_at_rest(link.node)
    ]


# --------------------------------------------------------------------------
# -- Weighting
# --------------------------------------------------------------------------
def split_matrix(matrix) -> tuple:
    """
    Returns (rotate/scale/shear part, translation vector) of a matrix.
    """
    matrix = om.MMatrix(matrix)
    translation = om.MVector(matrix.getElement(3, 0), matrix.getElement(3, 1), matrix.getElement(3, 2))

    rotate_scale = om.MMatrix(matrix)
    for column in range(3):
        rotate_scale.setElement(3, column, 0.0)

    return rotate_scale, translation


def compose(rotate_scale, translation) -> om.MMatrix:
    """
    Returns the matrix made from a rotate/scale/shear part and a
    translation vector.
    """
    matrix = om.MMatrix(rotate_scale)
    for column, value in enumerate(translation):
        matrix.setElement(3, column, value)
    return matrix


def unweight_rotate_scale(matrix, weight: float) -> tuple:
    """
    Returns the full rotate/scale/shear matrix which blendMatrix, at the
    given weight, blends to the given matrix: the inverse of its slerp (for
    the rotation) and lerp (for the scale and shear) from identity.

    Returns:
        (matrix, the full rotation angle in degrees)
    """
    transform = om.MTransformationMatrix(om.MMatrix(matrix))

    axis, angle = transform.rotation(asQuaternion=True).asAxisAngle()
    if angle > math.pi:
        angle -= 2.0 * math.pi
    full_angle = angle / weight

    result = om.MTransformationMatrix()
    result.setScale(
        [1.0 + (value - 1.0) / weight for value in transform.scale(om.MSpace.kTransform)],
        om.MSpace.kTransform,
    )
    result.setShear(
        [value / weight for value in transform.shear(om.MSpace.kTransform)],
        om.MSpace.kTransform,
    )
    result.setRotation(om.MQuaternion(full_angle, axis))

    return result.asMatrix(), math.degrees(full_angle)


def solve_pose_matrix(mixer, pose_name: str, link: DrivenLink, weight: float) -> tuple:
    """
    Returns the full pose matrix which, at the given weight and with every
    other pose held, reproduces the driven object's current offset and local
    channels together (so its channels can be zeroed).

    Returns:
        (pose matrix, list of warnings)
    """
    warnings = []
    pose_index = mixer.pose_index(pose_name)

    before = om.MMatrix()
    after = om.MMatrix()
    current_rotate_scale = om.MMatrix()
    current_translation = om.MVector()

    for index, matrix in mixer.chain_inputs(link.index):
        if index < matrix_mixer.TRANSLATE_OFFSET:
            if index < pose_index:
                before *= matrix
            elif index == pose_index:
                current_rotate_scale = matrix
            else:
                after *= matrix

        elif index == matrix_mixer.TRANSLATE_OFFSET + pose_index:
            current_translation = split_matrix(matrix)[1]

    local = om.MMatrix(cmds.getAttr(f"{link.node.full_name()}.matrix"))
    local_rotate_scale, local_translation = split_matrix(local)

    shear = max(abs(value) for value in om.MTransformationMatrix(local).shear(om.MSpace.kTransform))
    if shear > SHEAR_TOLERANCE:
        warnings.append(f"{link.node.name()} is sheared ({shear:.4f}), which is carried into the pose")

    all_rotate_scale = before * current_rotate_scale * after

    weighted_rotate_scale = before.inverse() * local_rotate_scale * before * current_rotate_scale
    weighted_translation = (local_translation * all_rotate_scale) + current_translation

    full_rotate_scale, full_angle = unweight_rotate_scale(weighted_rotate_scale, weight)

    if abs(full_angle) > 180.0:
        warnings.append(
            f"{link.node.name()} would need a {abs(full_angle):.0f} degree rotation at full weight, "
            f"which a pose cannot hold (180 at most). Edit it at a higher weight.",
        )

    return compose(full_rotate_scale, weighted_translation / weight), warnings


# --------------------------------------------------------------------------
# -- Mirroring
# --------------------------------------------------------------------------
def frame_axes(matrix) -> list:
    """
    Returns the normalised X, Y and Z axes of a matrix.
    """
    matrix = om.MMatrix(matrix)
    return [
        om.MVector(matrix.getElement(row, 0), matrix.getElement(row, 1), matrix.getElement(row, 2)).normal()
        for row in range(3)
    ]


def mirror_permutation(mixer, source, mirror) -> om.MMatrix:
    """
    Returns the signed permutation P taking coordinates in the source's rest
    frame to the mirror's (x_mirror = x_source * P), found by reflecting
    the source frame's axes across world X and matching each to the closest
    axis of the mirror's frame. No assumption is made about how the rig
    orients mirrored objects.

    Raises:
        ValueError: If the two frames are not symmetric enough to mirror
    """
    source_axes = frame_axes(mixer.rest_frame(source))
    mirror_axes = frame_axes(mixer.rest_frame(mirror))

    permutation = om.MMatrix()
    for row in range(3):
        permutation.setElement(row, row, 0.0)

    used = []
    for row, source_axis in enumerate(source_axes):
        reflected = om.MVector(-source_axis.x, source_axis.y, source_axis.z)
        alignments = [reflected * mirror_axis for mirror_axis in mirror_axes]
        column = max(range(3), key=lambda idx: abs(alignments[idx]))

        if abs(alignments[column]) < MIRROR_AXIS_ALIGNMENT or column in used:
            raise ValueError(
                f"{mixer.driven_key(source)} and {mixer.driven_key(mirror)} are not oriented symmetrically",
            )

        used.append(column)
        permutation.setElement(row, column, 1.0 if alignments[column] > 0 else -1.0)

    return permutation


def mirror_matrix(matrix, permutation) -> om.MMatrix:
    """
    Returns a pose matrix carried into the mirror's rest frame:
    P^-1 * M * P.
    """
    permutation = om.MMatrix(permutation)
    return permutation.transpose() * om.MMatrix(matrix) * permutation


def mirror_link(links, link) -> DrivenLink | None:
    """
    Returns the link of the driven object on the other side (its name with
    the side tokens swapped), or None if there is none.
    """
    for name in (mirror_name(link.node.name()), mirror_name(link.key)):
        for candidate in links:
            if candidate.node.name() == name or candidate.key == name:
                return candidate
    return None


# --------------------------------------------------------------------------
# -- Pose operations
# --------------------------------------------------------------------------
def update_pose(mixer, pose_name: str, links=None, mirror: bool = False) -> UpdateResult:
    """
    Bakes the current local transform of every moved driven object into the
    given pose, at the pose's current weight, then zeroes those objects.
    Objects already at rest are left alone, as are their pose matrices.

    When mirroring, each matrix written is also mirrored into the mirror
    pose (see mirror_name) for the mirror object, overwriting it. A centre
    pose mirrors onto itself, in which case centre objects, and objects
    which were themselves edited, are left as updated.

    Args:
        mixer: The MatrixMixer
        pose_name: The name of the pose to update
        links: The DrivenLinks of the mixer, if already resolved
        mirror: True to also write the mirrored matrices into the mirror pose

    Returns:
        An UpdateResult

    Raises:
        ValueError: If the pose's weight is too close to zero to edit
    """
    weight = mixer.weight_attribute(pose_name).get()

    if abs(weight) < MINIMUM_WEIGHT:
        raise ValueError(f"{pose_name} is at {weight:.0%}. Push it above {MINIMUM_WEIGHT:.0%} to edit it.")

    if links is None:
        links = resolve_links(mixer)

    result = UpdateResult()

    # -- Solve everything before writing anything. Writing a pose moves the
    # -- object it drives, and with it any driven object beneath that one.
    changes = []

    for link in links:
        if not link.editable or is_at_rest(link.node):
            continue

        if has_driven_channels(link.node):
            result.skipped.append((link.key, f"{link.node.name()} is keyed or driven, so it cannot be zeroed"))
            continue

        matrix, warnings = solve_pose_matrix(mixer, pose_name, link, weight)
        result.warnings.extend(warnings)
        changes.append((link, matrix))

    if not changes:
        return result

    if abs(weight) < LOW_WEIGHT:
        result.warnings.append(
            f"{pose_name} is at {weight:.0%}, so the edits were magnified {1.0 / abs(weight):.1f}x to reach its full weight",
        )

    mirror_changes = mirror_updates(mixer, pose_name, links, changes, result) if mirror else list()

    with undo_chunk(f"Update {pose_name}"):
        for link, matrix in changes:
            mixer.set_pose_matrix(pose_name, link.index, matrix)
            result.updated.append(link.key)

        for link, matrix in mirror_changes:
            mixer.set_pose_matrix(result.mirror_pose, link.index, matrix)
            result.mirrored.append(link.key)

        for link, _ in changes:
            matrix_mixer.zero_channels(link.node)

    return result


def mirror_updates(mixer, pose_name: str, links, changes, result) -> list:
    """
    Returns the mirror objects and mirrored matrices for the given changes
    to a pose, recording the mirror pose (and anything which cannot be
    mirrored) in the result.

    Args:
        mixer: The MatrixMixer
        pose_name: The name of the pose being updated
        links: The DrivenLinks of the mixer
        changes: (link, pose matrix) for each object being updated
        result: The UpdateResult

    Returns:
        A list of (mirror link, mirrored matrix)
    """
    mirror_pose = mirror_name(pose_name)

    if not mixer.get_pose(mirror_pose):
        result.warnings.append(f"There is no pose called {mirror_pose}, so nothing was mirrored")
        return list()

    result.mirror_pose = mirror_pose
    updated = [link.index for link, _ in changes]
    mirrored = []

    for link, matrix in changes:
        target = mirror_link(links, link)

        if not target:
            result.warnings.append(f"{link.key} was not mirrored: there is no driven object called {mirror_name(link.node.name())}")
            continue

        # -- A centre pose mirrors onto itself: a centre object would be its
        # -- own mirror, and an edited object keeps its own edit
        if mirror_pose == pose_name and (target.index == link.index or target.index in updated):
            continue

        try:
            permutation = mirror_permutation(mixer, link.index, target.index)

        except ValueError as error:
            result.warnings.append(f"{link.key} was not mirrored: {error}")
            continue

        mirrored.append((target, mirror_matrix(matrix, permutation)))

    return mirrored


def mirror_pose(mixer, pose_name: str, links=None) -> UpdateResult:
    """
    Writes the whole pose, mirrored, into its mirror pose: every driven
    object's matrix (identity included, so the mirror pose ends up an exact
    mirror) is mirrored onto its mirror object. Centre objects are mirrored
    onto themselves.

    Raises:
        ValueError: If the pose has no separate mirror pose
    """
    target_pose = mirror_name(pose_name)

    if target_pose == pose_name:
        raise ValueError(f"{pose_name} is a centre pose, so it has no other side to paste into")

    if not mixer.get_pose(target_pose):
        raise ValueError(f"There is no pose called {target_pose}")

    if links is None:
        links = resolve_links(mixer)

    result = UpdateResult(mirror_pose=target_pose)
    writes = []

    for link in links:
        target = mirror_link(links, link) or (link if mirror_name(link.node.name()) == link.node.name() else None)

        if not target:
            result.warnings.append(f"{link.key} was not mirrored: there is no driven object called {mirror_name(link.node.name())}")
            continue

        try:
            permutation = mirror_permutation(mixer, link.index, target.index)

        except ValueError as error:
            result.warnings.append(f"{link.key} was not mirrored: {error}")
            continue

        writes.append((target, mirror_matrix(mixer.pose_matrix(pose_name, link.index), permutation)))

    with undo_chunk(f"Mirror {pose_name}"):
        for target, matrix in writes:
            mixer.set_pose_matrix(target_pose, target.index, matrix)
            result.mirrored.append(target.key)

    return result


def reset_pose(mixer, pose_name: str) -> None:
    """
    Removes every matrix of the pose, so it no longer moves anything.
    """
    with undo_chunk(f"Reset {pose_name}"):
        for index in list(mixer.pose_matrices(pose_name)):
            mixer.set_pose_matrix(pose_name, index, om.MMatrix())


def add_pose(mixer, pose_name: str):
    """
    Adds an empty pose to the mixer, as a single undo step.
    """
    with undo_chunk(f"Add {pose_name}"):
        return mixer.add_pose(pose_name)


def remove_pose(mixer, pose_name: str) -> None:
    """
    Removes the pose from the mixer, as a single undo step.
    """
    with undo_chunk(f"Remove {pose_name}"):
        mixer.remove_pose(pose_name)


def read_data_file(path: str) -> dict:
    """
    Reads mixer data from a json file.

    Raises:
        ValueError: If the file does not hold mixer data
    """
    with open(path, "r") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"{path} does not hold mixer data")

    poses = data.get("poses")
    if not isinstance(poses, list) or not all(isinstance(pose, dict) and "name" in pose for pose in poses):
        raise ValueError(f"{path} does not hold mixer data (it has no list of named poses)")

    return data


def write_data_file(path: str, data: dict) -> None:
    """
    Writes mixer data (from MatrixMixer.serialise) to a json file.
    """
    with open(path, "w") as handle:
        json.dump(data, handle, indent=4)


def load_data(mixer, data: dict, keep_poses=()) -> list:
    """
    Replaces the mixer's poses with those in the data, as a single undo
    step. Poses which are not in the data are removed, apart from those in
    keep_poses (such as a component's built-in poses), which are emptied.
    Matrices for keys the mixer does not drive are not applied.

    Args:
        mixer: The MatrixMixer
        data: Data from MatrixMixer.serialise (or read_data_file)
        keep_poses: Poses which must not be removed

    Returns:
        The keys which have matrices in the data but are not driven
    """
    names = [pose_data["name"] for pose_data in data.get("poses", list())]

    with undo_chunk("Load Data"):
        for pose_name in mixer.pose_names():
            if pose_name in names or pose_name in keep_poses:
                for index in list(mixer.pose_matrices(pose_name)):
                    mixer.set_pose_matrix(pose_name, index, om.MMatrix())
            else:
                mixer.remove_pose(pose_name)

        return mixer.apply_data(data)


def add_driven(mixer, nodes) -> list:
    """
    Makes the mixer drive the given nodes, as a single undo step.

    Returns:
        (node name, reason) for every node which could not be added
    """
    problems = []

    with undo_chunk("Add Driven"):
        for node in nodes:
            try:
                mixer.add_driven(node)

            except ValueError as error:
                problems.append((mref.get(node).name(), str(error)))

    return problems


def remove_driven(mixer, nodes) -> None:
    """
    Stops the mixer driving the given nodes, as a single undo step.
    """
    with undo_chunk("Remove Driven"):
        for node in nodes:
            mixer.remove_driven(node)
