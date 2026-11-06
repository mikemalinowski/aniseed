"""
Editing TransformMixer poses (see pose_mixer.TransformMixer) through the
controls the mixer drives.

A mixer deformer drives the local channels of a control's offset (OFF_)
node. To edit a pose the user moves the control (CTL_) beneath that offset.
update_pose then folds the control's local transform into the offset,
solves the pose's target so that the mixer produces that offset at the
current pose weights, and zeroes the control. Nothing moves in world space.

Everything is solved in local space: the offset's parent can be constrained
or nested beneath other controls without affecting the result.

update_pose can also mirror what it writes onto the mirror pose (found by
swapping the side tokens in the names, see mirror_name). The mirrored
targets are written directly, so the mirror pose does not need any weight.
"""
import math
import logging
import contextlib
import dataclasses

import mref
from maya.api import OpenMaya as om

log = logging.getLogger(__name__)

# -- An edit is divided by the pose weight, so below this (absolute) weight
# -- it would be magnified beyond use and the pose cannot be edited
MINIMUM_WEIGHT = 0.05

# -- Below this (absolute) weight an edit still works, but is noticeably
# -- magnified, so the user is warned
LOW_WEIGHT = 0.5

# -- Channel values within this of their rest value count as being at rest
TOLERANCE = 1e-5

# -- Shear above this cannot be represented by the channels and is reported
SHEAR_TOLERANCE = 1e-4

# -- Every undo chunk opened here starts with this, so a tool can tell when
# -- one of its edits has been undone or redone
UNDO_CHUNK_PREFIX = "TransformMixerPoseEdit"

OFFSET_PREFIX = "OFF_"
CONTROL_PREFIX = "CTL_"

REST_VALUES = {
    "translate": (0.0, 0.0, 0.0),
    "rotate": (0.0, 0.0, 0.0),
    "scale": (1.0, 1.0, 1.0),
}

TRANSFORM_CHANNELS = [
    f"{channel}{axis}"
    for channel in REST_VALUES
    for axis in "XYZ"
]

# -- Name tokens (split on underscores, compared without case) which mark a
# -- side, and the token of the opposite side
SIDE_TOKENS = {
    "left": "right",
    "right": "left",
    "lf": "rt",
    "rt": "lf",
}

# -- Each local axis of an offset must line up with an axis of its mirror
# -- offset (once reflected across world X) to at least this dot product,
# -- otherwise the pair is not symmetric enough to mirror. This allows for
# -- small asymmetries in how the rig was built.
MIRROR_AXIS_ALIGNMENT = 0.95

# -- Maya's rotate order enumeration
ROTATE_ORDERS = ["xyz", "yzx", "zxy", "xzy", "yxz", "zyx"]


@dataclasses.dataclass
class DeformerLink:
    """
    A mixer deformer, the node it drives and the control the user edits in
    its place. When the deformer cannot be edited, control is None and
    problem says why.
    """
    deformer_name: str
    deformer: mref.ReferencedItem
    driven: mref.ReferencedItem | None = None
    control: mref.ReferencedItem | None = None
    problem: str = ""


@dataclasses.dataclass
class UpdateResult:
    """
    The outcome of update_pose: the deformers whose targets were updated,
    the (deformer name, reason) pairs which were skipped, and any warnings.
    When mirroring, also the mirror pose and the deformers written in it.
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


@contextlib.contextmanager
def unlocked(nodes):
    """
    Unlocks the given nodes and their translate, rotate and scale channels
    for the duration of the block, then restores the locks they had on those
    which still exist. Rigs commonly lock the mixer targets.

    Args:
        nodes: The nodes (mref items) to unlock
    """
    locked_nodes = [
        node
        for node in nodes
        if node.is_locked()
    ]
    locked_channels = [
        node.attr(channel_name)
        for node in nodes
        for channel_name in TRANSFORM_CHANNELS
        if node.attr(channel_name).is_locked()
    ]

    # -- A locked node's attribute locks cannot be changed, so the node is
    # -- unlocked first and locked again last
    for node in locked_nodes:
        node.unlock()

    for attribute in locked_channels:
        attribute.unlock()

    try:
        yield

    finally:
        for attribute in locked_channels:
            if attribute.node().exists():
                attribute.lock()

        for node in locked_nodes:
            if node.exists():
                node.lock()


def resolve_links(mixer):
    """
    Follows each of the mixer's deformers to the node it drives and, where
    that is an offset node, to the control beneath it.

    Args:
        mixer: The TransformMixer

    Returns:
        A DeformerLink per deformer, in the mixer's deformer order
    """
    links = []

    for deformer in mixer.deformers():
        link = DeformerLink(
            deformer_name=deformer.attr("deformer_name").get(),
            deformer=deformer,
        )
        links.append(link)

        # -- Unit conversion nodes are skipped by outputs()
        driven = deformer.attr("translate").outputs()
        if not driven:
            link.problem = "does not drive anything"
            continue

        link.driven = driven[0].node()

        if not link.driven.name().startswith(OFFSET_PREFIX):
            link.problem = f"drives {link.driven.name()}, which is not an {OFFSET_PREFIX} node"
            continue

        controls = [
            child
            for child in link.driven.children(node_type="transform", include_shapes=False)
            if child.name().startswith(CONTROL_PREFIX)
        ]
        if not controls:
            link.problem = f"{link.driven.name()} has no {CONTROL_PREFIX} child"
            continue

        link.control = controls[0]

        # -- The face component also links each control to its deformer. The
        # -- hierarchy is what is solved against, so a mismatch is only reported
        if deformer.has_attribute("control_link"):
            linked = deformer.attr("control_link").inputs()

            if linked and linked[0].node() != link.control:
                log.warning(
                    f"{deformer.name()} is linked to {linked[0].node().name()} but drives "
                    f"{link.driven.name()}, whose control is {link.control.name()}. "
                    f"Using {link.control.name()}."
                )

        for node in [link.driven, link.control]:
            if not channels_match_matrix(node):
                link.problem = (
                    f"the local matrix of {node.name()} is not made from its translate, "
                    f"rotate and scale alone (pivots, rotate axis or joint orient)"
                )
                link.control = None
                break

    return links


def channels(node):
    """
    Returns the node's translate, rotate (in degrees) and scale as a
    dictionary of (x, y, z) tuples.
    """
    return {
        channel: tuple(node.attr(channel).get()[0])
        for channel in REST_VALUES
    }


def is_at_rest(node):
    """
    Returns True if the node's translate, rotate and scale are all at their
    rest values.
    """
    return all(
        abs(value - rest) < TOLERANCE
        for channel, values in channels(node).items()
        for value, rest in zip(values, REST_VALUES[channel])
    )


def channels_match_matrix(node):
    """
    Returns True if the node's local matrix is exactly its translate, rotate
    and scale. Pivots, a rotate axis or a joint orient break this, and the
    solve relies on it.
    """
    values = channels(node)

    transform = om.MTransformationMatrix()
    transform.setTranslation(om.MVector(values["translate"]), om.MSpace.kTransform)
    transform.setRotation(
        om.MEulerRotation(
            [math.radians(value) for value in values["rotate"]],
            node.attr("rotateOrder").get(),
        ),
    )
    transform.setScale(values["scale"], om.MSpace.kTransform)

    return transform.asMatrix().isEquivalent(
        om.MMatrix(node.attr("matrix").get()),
        1e-4,
    )


def has_driven_channels(node):
    """
    Returns True if any of the node's translate, rotate or scale channels
    has an input (such as animation), which would undo the zeroing.
    """
    for channel in REST_VALUES:
        if node.attr(channel).inputs():
            return True

        for axis in "XYZ":
            if node.attr(f"{channel}{axis}").inputs():
                return True

    return False


def offset_including_control(link):
    """
    Returns the offset channels which reproduce the offset and control
    together once the control is zeroed, along with the largest shear
    component (which the channels cannot hold).

    The rotation uses the offset's rotate order, and of the equivalent Euler
    solutions the one closest to the offset's current rotation, so nothing
    flips by 360 degrees.

    Args:
        link: An editable DeformerLink

    Returns:
        (channels dictionary, largest absolute shear)
    """
    # -- Maya matrices are row-vector: the child's local matrix comes first
    control_matrix = om.MMatrix(link.control.attr("matrix").get())
    offset_matrix = om.MMatrix(link.driven.attr("matrix").get())
    transform = om.MTransformationMatrix(control_matrix * offset_matrix)

    rotate_order = link.driven.attr("rotateOrder").get()
    current_rotation = channels(link.driven)["rotate"]

    rotation = transform.rotation(asQuaternion=True).asEulerRotation()
    rotation.reorderIt(rotate_order)
    rotation.setToClosestSolution(
        om.MEulerRotation(
            [math.radians(value) for value in current_rotation],
            rotate_order,
        ),
    )

    desired = {
        "translate": tuple(transform.translation(om.MSpace.kTransform)),
        "rotate": (
            math.degrees(rotation.x),
            math.degrees(rotation.y),
            math.degrees(rotation.z),
        ),
        "scale": tuple(transform.scale(om.MSpace.kTransform)),
    }
    shear = max(abs(value) for value in transform.shear(om.MSpace.kTransform))

    return desired, shear


def zero_channels(node):
    """
    Sets the node's translate and rotate to zero and its scale to one,
    skipping any channel which is locked.
    """
    for channel, rest_values in REST_VALUES.items():
        for axis, rest_value in zip("XYZ", rest_values):
            attribute = node.attr(f"{channel}{axis}")

            if not attribute.is_locked():
                attribute.set(rest_value)


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
class MirrorMapping:
    """
    How the local channels of an offset map onto its mirror offset: local
    axis i of the source becomes axis permutation[i] of the mirror, scaled
    by signs[i]. determinant is -1 when the mapping is a reflection, which
    reverses the direction of every rotation.
    """
    permutation: list
    signs: list
    determinant: float


def rest_parent_axes(node):
    """
    Returns the normalised world space X, Y and Z axes of the node's parent
    (the axes its local channels are expressed in) with the rig at rest:
    every offset and control above it is taken as untransformed, so whatever
    the mixer or the animator is currently doing does not matter.
    """
    # -- Maya matrices are row-vector: the child's local matrix comes first
    matrix = om.MMatrix()
    parent = node.parent()

    while parent:
        if not parent.name().startswith((OFFSET_PREFIX, CONTROL_PREFIX)):
            matrix *= om.MMatrix(parent.attr("matrix").get())
        parent = parent.parent()

    return [
        om.MVector(matrix.getElement(row, 0), matrix.getElement(row, 1), matrix.getElement(row, 2)).normal()
        for row in range(3)
    ]


def mirror_mapping(source, mirror):
    """
    Works out how the local channels of the source offset map onto the
    mirror offset, by reflecting the source's parent axes (at rest) across
    world X and matching each to the closest of the mirror's parent axes.
    This makes no assumption about how the rig orients its mirrored nodes.

    Args:
        source: The source offset node
        mirror: The mirror offset node (the same node for a centre offset)

    Returns:
        A MirrorMapping

    Raises:
        ValueError: If the two are not symmetric enough to mirror between
    """
    mirror_axes = rest_parent_axes(mirror)
    permutation = []
    signs = []

    for source_axis in rest_parent_axes(source):
        reflected = om.MVector(-source_axis.x, source_axis.y, source_axis.z)
        alignments = [
            reflected * mirror_axis
            for mirror_axis in mirror_axes
        ]
        index = max(range(3), key=lambda idx: abs(alignments[idx]))

        if abs(alignments[index]) < MIRROR_AXIS_ALIGNMENT:
            raise ValueError(
                f"{source.name()} and {mirror.name()} are not oriented symmetrically",
            )

        permutation.append(index)
        signs.append(1.0 if alignments[index] > 0 else -1.0)

    if sorted(permutation) != [0, 1, 2]:
        raise ValueError(
            f"{source.name()} and {mirror.name()} are not oriented symmetrically",
        )

    # -- The channels are mirrored one by one, which only holds when the
    # -- mirror rotates its (swapped) axes in the same order
    source_order = ROTATE_ORDERS[source.attr("rotateOrder").get()]
    swapped_order = "".join(
        "xyz"[permutation["xyz".index(axis)]]
        for axis in source_order
    )
    if swapped_order != ROTATE_ORDERS[mirror.attr("rotateOrder").get()]:
        raise ValueError(
            f"{mirror.name()} would need the rotate order {swapped_order} to mirror {source.name()}",
        )

    inversions = sum(
        1
        for a in range(3)
        for b in range(a + 1, 3)
        if permutation[a] > permutation[b]
    )
    determinant = (-1.0) ** inversions * math.prod(signs)

    return MirrorMapping(permutation=permutation, signs=signs, determinant=determinant)


def mirror_channels(values, mapping):
    """
    Returns the given channels (as from channels()) mirrored through the
    given MirrorMapping. Each channel maps onto one channel, so a sum of
    targets mirrors to the sum of their mirrors, as the mixer requires.
    """
    mirrored = {
        channel: [0.0, 0.0, 0.0]
        for channel in REST_VALUES
    }

    for axis, (index, sign) in enumerate(zip(mapping.permutation, mapping.signs)):
        mirrored["translate"][index] = sign * values["translate"][axis]
        mirrored["rotate"][index] = mapping.determinant * sign * values["rotate"][axis]
        mirrored["scale"][index] = values["scale"][axis]

    return {
        channel: tuple(axis_values)
        for channel, axis_values in mirrored.items()
    }


def update_pose(mixer, pose_name, links=None, mirror=False):
    """
    Bakes the current local transform of every edited control into the
    given pose, at the pose's current weight, then zeroes those controls.
    Controls already at rest are left alone, as are their targets.

    The mixer sums each target's channels multiplied by its pose weight, so
    with the offset's current channels being that sum, the pose's target
    changes by (desired - current) / weight on every channel.

    When mirroring, each target written is also mirrored onto the mirror
    deformer's target in the mirror pose (see mirror_name), overwriting it.
    A centre pose mirrors onto itself, in which case centre deformers, and
    deformers whose own control was edited, are left as updated.

    Args:
        mixer: The TransformMixer
        pose_name: The name of the pose to update
        links: The DeformerLinks of the mixer, if already resolved
        mirror: True to also write the mirrored targets into the mirror pose

    Returns:
        An UpdateResult

    Raises:
        ValueError: If the pose's weight is too close to zero to edit
    """
    weight = mixer.node.attr(pose_name).get()

    if abs(weight) < MINIMUM_WEIGHT:
        raise ValueError(
            f"{pose_name} is at {weight:.0%}. Push it above {MINIMUM_WEIGHT:.0%} to edit it."
        )

    if links is None:
        links = resolve_links(mixer)

    result = UpdateResult()

    # -- Read every control and offset before writing anything. Writing a
    # -- target moves the offset it drives, and with it every control
    # -- parented beneath that offset.
    changes = []

    for link in links:
        if not link.control or is_at_rest(link.control):
            continue

        if has_driven_channels(link.control):
            result.skipped.append(
                (link.deformer_name, f"{link.control.name()} is keyed or driven, so it cannot be zeroed"),
            )
            continue

        target = mixer.get_target(pose_name, link.deformer_name)

        if not target:
            result.skipped.append(
                (link.deformer_name, "has no target for this pose (the targets may have been optimised away)"),
            )
            continue

        desired, shear = offset_including_control(link)

        if shear > SHEAR_TOLERANCE:
            result.warnings.append(
                f"{link.control.name()} adds shear ({shear:.4f}), which the pose cannot hold, so it was dropped",
            )

        changes.append((link, target, desired, channels(link.driven)))

    if changes and abs(weight) < LOW_WEIGHT:
        result.warnings.append(
            f"{pose_name} is at {weight:.0%}, so the edits were magnified {1.0 / abs(weight):.1f}x "
            f"to reach its full weight",
        )

    if not changes:
        return result

    updates = [
        (
            link,
            target,
            {
                channel: tuple(
                    value + (desired_value - current_value) / weight
                    for value, desired_value, current_value in zip(
                        target.attr(channel).get()[0],
                        desired[channel],
                        current[channel],
                    )
                )
                for channel in REST_VALUES
            },
        )
        for link, target, desired, current in changes
    ]

    mirror_updates = mirror_targets(mixer, pose_name, links, updates, result) if mirror else list()

    targets = [
        target
        for _, target, _ in updates + mirror_updates
    ]

    with undo_chunk(f"Update {pose_name}"), unlocked(targets):
        for link, target, values in updates:
            for channel, channel_values in values.items():
                target.attr(channel).set(*channel_values)
            result.updated.append(link.deformer_name)

        for link, target, values in mirror_updates:
            for channel, channel_values in values.items():
                target.attr(channel).set(*channel_values)
            result.mirrored.append(link.deformer_name)

        for link, _, _ in updates:
            zero_channels(link.control)

    return result


def mirror_targets(mixer, pose_name, links, updates, result):
    """
    Returns the mirror pose's targets for the given updates, with the
    mirrored values to write into them. Anything which cannot be mirrored is
    reported in the result's warnings.

    Args:
        mixer: The TransformMixer
        pose_name: The name of the pose being updated
        links: The DeformerLinks of the mixer
        updates: (link, target, channel values) for each target being updated
        result: The UpdateResult, which is given the mirror pose and warnings

    Returns:
        A list of (mirror link, mirror target, mirrored channel values)
    """
    mirror_pose = mirror_name(pose_name)
    pose_names = [
        pose.attr("pose_name").get()
        for pose in mixer.poses()
    ]

    if mirror_pose not in pose_names:
        result.warnings.append(f"There is no pose called {mirror_pose}, so nothing was mirrored")
        return list()

    result.mirror_pose = mirror_pose

    links_by_name = {
        link.deformer_name: link
        for link in links
    }
    updated_names = [
        link.deformer_name
        for link, _, _ in updates
    ]
    mirror_updates = []

    for link, _, values in updates:
        mirror_deformer = mirror_name(link.deformer_name)

        # -- A centre pose mirrors onto itself: a centre deformer would be
        # -- its own mirror, and an edited deformer keeps its own edit
        if mirror_pose == pose_name:
            if mirror_deformer == link.deformer_name or mirror_deformer in updated_names:
                continue

        mirror_link = links_by_name.get(mirror_deformer)

        if not mirror_link:
            result.warnings.append(f"{link.deformer_name} was not mirrored: there is no deformer called {mirror_deformer}")
            continue

        if not mirror_link.control:
            result.warnings.append(f"{link.deformer_name} was not mirrored: {mirror_deformer} {mirror_link.problem}")
            continue

        mirror_target = mixer.get_target(mirror_pose, mirror_deformer)

        if not mirror_target:
            result.warnings.append(f"{link.deformer_name} was not mirrored: {mirror_pose} has no target for {mirror_deformer}")
            continue

        try:
            mapping = mirror_mapping(link.driven, mirror_link.driven)

        except ValueError as error:
            result.warnings.append(f"{link.deformer_name} was not mirrored: {error}")
            continue

        mirror_updates.append((mirror_link, mirror_target, mirror_channels(values, mapping)))

    return mirror_updates


def pose_targets(mixer, pose_name):
    """
    Returns the targets of the given pose, in the mixer's deformer order.
    """
    return [
        target
        for deformer in mixer.deformers()
        if (target := mixer.get_target(pose_name, deformer.attr("deformer_name").get()))
    ]


def reset_pose(mixer, pose_name):
    """
    Returns every target of the given pose to rest, so the pose no longer
    moves anything.
    """
    targets = pose_targets(mixer, pose_name)

    with undo_chunk(f"Reset {pose_name}"), unlocked(targets):
        for target in targets:
            zero_channels(target)


def add_pose(mixer, pose_name):
    """
    Adds a pose to the mixer. Its targets start at rest, and are given the
    same node and channel locks as the mixer's existing targets.

    Args:
        mixer: The TransformMixer
        pose_name: The name of the new pose
    """
    existing_targets = list(mixer.get_target_mapping().values())
    template = existing_targets[0] if existing_targets else None

    with undo_chunk(f"Add {pose_name}"):
        mixer.add_pose(pose_name)

        if not template:
            return

        locked_channels = [
            channel_name
            for channel_name in TRANSFORM_CHANNELS
            if template.attr(channel_name).is_locked()
        ]
        for target in pose_targets(mixer, pose_name):
            target.lock_attributes(locked_channels)

            if template.is_locked():
                target.lock()


def remove_pose(mixer, pose_name):
    """
    Removes the pose, its targets and its weight attribute from the mixer,
    unlocking the targets first so they can be deleted.

    Args:
        mixer: The TransformMixer
        pose_name: The name of the pose to remove
    """
    targets = pose_targets(mixer, pose_name)

    with undo_chunk(f"Remove {pose_name}"), unlocked(targets + [mixer.get_pose(pose_name)]):
        mixer.remove_pose(pose_name)


def pose_controls(mixer, pose_name, links):
    """
    Returns the controls whose deformer the given pose moves (the controls
    of every target in the pose which is not at rest).
    """
    return [
        link.control
        for link in links
        if link.control
        if (target := mixer.get_target(pose_name, link.deformer_name)) and not is_at_rest(target)
    ]


def edited_controls(links):
    """
    Returns the controls which are away from rest, and so hold edits which
    have not been baked into a pose yet.
    """
    return [
        link.control
        for link in links
        if link.control
        if not is_at_rest(link.control)
    ]
