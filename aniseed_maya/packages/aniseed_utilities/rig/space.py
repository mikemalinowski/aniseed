"""
Space helpers for rigs: finding the root (world) control, and building space
switches which let a node follow one of several targets.
"""
import typing

from maya import cmds
import mref

from ..core import attributes as _attributes
from . import control as _control

if typing.TYPE_CHECKING:
    import aniseed


def create_space_switch(
        driven: str,
        host: str,
        spaces: list,
        default_space: str,
        config: "aniseed.RigConfiguration",
) -> None:
    """
    Adds a "spaces" enum attribute to the host and drives the given node
    through a parent (and optionally scale) constraint per space, with each
    constraint weight switched on by its space's index.

    If the driven node is part of a control, the control's org is driven.

    Each space is a dictionary of the form:

        {
            "target": "foobar",
            "position_only": False,
            "orientation_only": False,
            "target_transform": None,
            "label": "",
            "include_scale": True,
        }

    where target and target_transform are node names. If a target transform
    is given, a transform is created under the target, placed at the target
    transform and constrained to without offset,
    with the driven node moved there whilst constraining. The position only
    and orientation only flags apply to every space if any space sets them.

    Args:
        driven: The node to drive
        host: The node to add the "spaces" attribute to
        spaces: The spaces, in the order they appear in the attribute
        default_space: The label of the space which is active by default
        config: The aniseed.RigConfiguration instance, used to name the
            target transform locators
    """
    _attributes.add_separator(host)

    # -- If the node to drive is part of a control we drive its org
    control = _control.get(driven)
    if control:
        driven = control.org
    node_to_drive = mref.get(driven)

    spaces_attribute = mref.get(host).add_attribute(
        "spaces",
        value=None,
        attribute_type="enum",
        enumName=":".join(space["label"] for space in spaces),
        keyable=True,
    )

    orientation_only = False
    position_only = False

    default_space_idx = 0
    all_constraints = []

    for idx, space in enumerate(spaces):

        if space["orientation_only"]:
            orientation_only = True

        if space["position_only"]:
            position_only = True

        if space["label"] == default_space:
            default_space_idx = idx

        target = space["target"]
        target_transform = space["target_transform"]

        matrix_to_restore = None
        maintain_offset = True

        # -- If we're given a target transform, we constrain to a point
        # -- under the target at that transform, with the node to drive
        # -- moved there whilst constraining
        if target_transform:
            target = mref.create(
                "transform",
                name=config.generate_name(
                    classification="loc",
                    description="target_point",
                    location=config.middle,
                ),
                parent=target or None,
            )

            matrix_to_restore = node_to_drive.get_matrix(space="world")
            target.match_to(target_transform)
            maintain_offset = False

        constraints = [
            mref.parentConstraint(
                target,
                node_to_drive,
                maintainOffset=maintain_offset,
            )[0],
        ]

        if space["include_scale"]:
            constraints.append(
                mref.scaleConstraint(
                    target,
                    node_to_drive,
                    maintainOffset=maintain_offset,
                )[0]
            )

        for constraint in constraints:

            # -- The condition nodes are left unnamed
            condition = mref.create("condition")
            condition.secondTerm.set(idx)
            condition.colorIfTrueR.set(1)
            condition.colorIfFalseR.set(0)

            # -- The constraint type is identified by Maya's default
            # -- constraint naming, so a driven node with "scale" in its
            # -- name breaks this (the alias query returns None)
            weight_query = cmds.scaleConstraint if "scale" in constraint.name() else cmds.parentConstraint
            weight_alias = weight_query(constraint.full_name(), query=True, weightAliasList=True)[-1]

            # -- connectAttr rather than Attribute.connect so that a
            # -- failed connection still raises
            mref.connectAttr(spaces_attribute, condition.firstTerm)
            mref.connectAttr(condition.outColorR, constraint.attr(weight_alias))

        if matrix_to_restore:
            node_to_drive.set_matrix(matrix_to_restore, space="world")

        all_constraints.extend(constraints)

    if position_only:
        _disconnect_channel(all_constraints, node_to_drive, "rotate")

    if orientation_only:
        _disconnect_channel(all_constraints, node_to_drive, "translate")

    spaces_attribute.set(default_space_idx)


def _disconnect_channel(constraints, driven, channel):
    """
    Breaks the connections from each constraint's output to the given
    channel ("translate" or "rotate") of the driven node.
    """
    constraint_channel = "constraint" + channel.title()

    for constraint in constraints:
        for axis in "XYZ":
            source = constraint.attr(f"{constraint_channel}{axis}")

            # -- Scale constraints have no translate / rotate outputs
            if not source:
                continue

            try:
                source.disconnect(driven.attr(f"{channel}{axis}"))

            except RuntimeError:
                # -- Channel wasn't connected on this constraint;
                # -- nothing to disconnect, fine to skip.
                pass


def setup_fk_worldspace_switches(nodes: list, config: "aniseed.RigConfiguration") -> None:
    """
    Adds an orientation space switch to each of the given fk controls,
    allowing them to switch between following their parent and the world.
    """
    _setup_fk_switches(nodes, config, orientation_only=True, default_space="Parent")


def setup_fk_transform_worldspace_switches(
        nodes: list,
        config: "aniseed.RigConfiguration",
        default_space: str = "Parent",
) -> None:
    """
    Adds a full transform space switch to each of the given fk controls,
    allowing them to switch between following their parent and the world.
    """
    _setup_fk_switches(nodes, config, orientation_only=False, default_space=default_space)


def _setup_fk_switches(nodes, config, orientation_only: bool, default_space: str):
    nodes = [mref.get(node) for node in nodes]

    # -- The first node's space parent is whatever its control sits under,
    # -- after that, each node's parent space is the previous node
    parent = mref.get(_control.get(nodes[0].name()).org).parent()
    world = get_root_control()

    for node in nodes:

        # -- Add a space switch on this node with the default being the parent
        # -- and the alternate being the world.
        create_space_switch(
            driven=node.name(),
            host=node.name(),
            spaces=[
                {
                    "target": parent.name(),
                    "position_only": False,
                    "orientation_only": orientation_only,
                    "target_transform": "",
                    "label": "Parent",
                    "include_scale": False,
                },
                {
                    "target": world,
                    "position_only": False,
                    "orientation_only": orientation_only,
                    "target_transform": "",
                    "label": "World",
                    "include_scale": False,
                }
            ],
            default_space=default_space,
            config=config,
        )

        parent = node


def get_root_control():
    """
    Returns the controller transform with the smallest hierarchy depth.

    Priority:
    1. Maya controller tags
    2. *_CTRL naming convention fallback

    Returns:
        str or None
    """
    controls = set()

    # --- Get controls from Maya controller tags ---
    for tag in mref.ls(type="controller") or []:
        source = tag.attr("controllerObject").source()
        if source:
            controls.add(source.node())

    # --- Fallback naming convention ---
    controls.update(mref.ls("*_CTRL", type="transform") or [])

    if not controls:
        return None

    # -- The depth is measured by the number of nodes in the dag path
    shallowest = min(controls, key=lambda node: node.full_name().count("|"))

    return shallowest.name()
