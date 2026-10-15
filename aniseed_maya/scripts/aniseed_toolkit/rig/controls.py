"""
Queries across the controls of aniseed rigs: finding all controls, the rig a
node belongs to, opposing controls, controls by location, and mirroring
control shapes by name.
"""
from maya import cmds

from ..registry import tool
from . import control as _control
from ..scene import shapes as _shapes


@tool(
    "Get Controls",
    classification="Animation",
    user_facing=False,
)
def all_controls(namespace: str = "") -> list[str]:
    controls = []

    for control_node in cmds.controller(query=True, allControllers=True):
        if namespace and not control_node.startswith(namespace):
            continue

        root_node = cmds.ls(control_node, long=True)[0].split("|")[1]
        if cmds.objExists(f"{root_node}.aniseed_rig"):
            controls.append(control_node)

    return controls


@tool(
    "Resolve Rig Node",
    classification="Animation",
    user_facing=False,
)
def get_rig_node(node: str = "") -> str:
    full_node_path = cmds.ls(node, long=True)[0].split("|")

    for potential_rig_node in reversed(full_node_path):
        if cmds.objExists(f"{potential_rig_node}.aniseed_rig"):
            return potential_rig_node
    return ""


def get(node):
    """
    Returns the aniseed Rig which the given node belongs to, or None if it
    is not part of an aniseed rig.
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
    This will return the opposite controls for the given controls

    Args:
        controls: List of controls to get the opposites for. If none are
            given then the selection will be used.
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
    This will return the opposite controls for the given controls

    Args:
        controls: List of controls to get the opposites for. If none are
            given then the selection will be used.
    """
    filtered_controls = []
    rig = None

    if not controls:
        reference_node = cmds.ls(selection=True)[0]
    else:
        reference_node = controls[0]

    # -- Get the rig
    location_filter = None
    control_node = _control.get(reference_node)
    rig = get(control_node.ctl)
    location_filter = control_node.location

    for node in all_controls():
        control_instance = _control.get(node)
        if not control_instance:
            continue

        if control_instance.location == location_filter:
            filtered_controls.append(control_instance.ctl)

    return filtered_controls


def mirror_control_shapes(mapping: str = "_LF:_RT", axis="x"):

    from_tag = mapping.split(":")[0]
    to_tag = mapping.split(":")[1]

    for node in all_controls():
        if from_tag not in node:
            continue

        to_node = node.replace(from_tag, to_tag)

        if not cmds.objExists(to_node):
            continue

        _shapes.mirror_across(
            from_nodes=[node],
            to_nodes=[to_node],
            axis=axis,
        )
