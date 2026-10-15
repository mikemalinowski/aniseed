"""
Queries across the controls of aniseed rigs: finding all controls, the rig a
node belongs to, opposing controls, controls by location, and mirroring
control shapes by name.

Note: node names are returned exactly as maya reports them (short names, or
partial paths where a short name is not unique), so the maya queries which
return node names use cmds rather than mref.
"""
from maya import cmds
import mref

from ..registry import tool
from . import control as _control
from ..scene import shapes as _shapes


@tool(
    "Get Controls",
    classification="Animation",
    user_facing=False,
)
def all_controls(namespace: str = "") -> list[str]:
    """
    Returns every controller tagged node in the scene which belongs to an
    aniseed rig (i.e. whose top level node has an aniseed_rig attribute).

    Args:
        namespace: If given, only controls whose name starts with this
            string are returned.

    Returns:
        The names of the controls, as maya reports them
    """
    controls = []

    for control_node in cmds.controller(query=True, allControllers=True):
        if namespace and not control_node.startswith(namespace):
            continue

        root_node = cmds.ls(control_node, long=True)[0].split("|")[1]
        if mref.objExists(f"{root_node}.aniseed_rig"):
            controls.append(control_node)

    return controls


@tool(
    "Resolve Rig Node",
    classification="Animation",
    user_facing=False,
)
def get_rig_node(node: str = "") -> str:
    """
    Returns the aniseed rig node which the given node sits beneath - the
    closest node in its hierarchy (including the node itself) which has an
    aniseed_rig attribute.

    Args:
        node: The node to find the rig node for

    Returns:
        The short name of the rig node, or an empty string if the node is
        not part of an aniseed rig.
    """
    full_node_path = cmds.ls(node, long=True)[0].split("|")

    for potential_rig_node in reversed(full_node_path):
        if mref.objExists(f"{potential_rig_node}.aniseed_rig"):
            return potential_rig_node
    return ""


def get(node):
    """
    Returns the aniseed Rig which the given node belongs to, or None if it
    is not part of an aniseed rig. This requires aniseed to be importable.

    Args:
        node: Any node within the rig

    Returns:
        aniseed.Rig or None
    """
    # -- aniseed is imported here rather than at module level so that the
    # -- toolkit can be imported (and used) without aniseed
    import aniseed

    rig_node = get_rig_node(node)

    if not rig_node:
        return None

    return aniseed.Rig(host=rig_node)


@tool(
    "Get Opposites",
    classification="Animation",
    categories=["Selection", "Controls"],
    user_facing=False,
)
def opposing_controls(controls: list[str] or None = None) -> list[str]:
    """
    This will return the names of the opposite controls for the given
    controls, using the configuration of the rig the first control belongs
    to. Any control which is not on the left is given the left location,
    and left controls are given the right location.

    The names are generated from the rig configuration, so they are not
    guaranteed to exist.

    Args:
        controls: List of controls to get the opposites for. This must be
            given (None raises an error).

    Returns:
        List of opposite control names
    """
    opposites = []
    rig_instance = None
    rig_config = None

    for node in controls:

        node = _control.get(node)

        if not node:
            continue

        # -- Get the rig
        if not rig_instance:
            rig_instance = get(node.ctl)
            rig_config = rig_instance.config()

        # -- Get the location of the control
        name_decomposition = rig_config.decomposition(node.ctl)

        # -- Now use the rig's config
        side = rig_config.left
        if name_decomposition["location"] == rig_config.left:
            side = rig_config.right

        name_decomposition["location"] = side
        opposite_control = rig_config.generate_name(
            unique=False,
            **name_decomposition
        )
        opposites.append(opposite_control)

    return opposites


def controls_by_location(controls: list[str] or None = None) -> list[str]:
    """
    Returns all the rig controls in the scene which share the location of
    the first of the given controls.

    Args:
        controls: List of controls, of which the first defines the location
            to filter by. If none are given then the first selected node
            is used.

    Returns:
        The ctl names of the controls with the same location
    """
    filtered_controls = []

    if not controls:
        reference_node = cmds.ls(selection=True)[0]
    else:
        reference_node = controls[0]

    control_node = _control.get(reference_node)

    # -- The rig is resolved (which requires aniseed) even though only the
    # -- location of the control is used
    get(control_node.ctl)
    location_filter = control_node.location

    for node in all_controls():
        control_instance = _control.get(node)
        if not control_instance:
            continue

        if control_instance.location == location_filter:
            filtered_controls.append(control_instance.ctl)

    return filtered_controls


def mirror_control_shapes(mapping: str = "_LF:_RT", axis="x"):
    """
    Mirrors the shapes of every rig control whose name contains the "from"
    tag onto the control with the same name but the "to" tag, if one
    exists.

    Args:
        mapping: The from and to name tags, separated by a colon
        axis: The axis to mirror the shapes across
    """
    from_tag = mapping.split(":")[0]
    to_tag = mapping.split(":")[1]

    for node in all_controls():
        if from_tag not in node:
            continue

        to_node = node.replace(from_tag, to_tag)

        if not mref.objExists(to_node):
            continue

        _shapes.mirror_across(
            from_nodes=[node],
            to_nodes=[to_node],
            axis=axis,
        )
