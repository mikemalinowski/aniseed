import aniseed
from maya import cmds
from . import control


def all_controls():
    controls = []

    for control_node in cmds.controller(query=True, allControllers=True):
        print("control node : %s" % control_node)
        root_node = cmds.ls(control_node, long=True)[0].split("|")[1]
        print("    root node : %s" % root_node)
        if cmds.objExists(f"{root_node}.aniseed_rig"):
            controls.append(control_node)

    return controls


def get_rig_node(node: str = "") -> str:
    full_node_path = cmds.ls(node, long=True)[0].split("|")

    for potential_rig_node in reversed(full_node_path):
        if cmds.objExists(f"{potential_rig_node}.aniseed_rig"):
            return potential_rig_node
    return ""


def get(node):
    rig_node = get_rig_node(node)

    if not rig_node:
        return None

    return aniseed.Rig(host=rig_node)


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

        node = control.get(node)

        if not node:
            continue

        # -- Get the rig
        if not rig_instance:
            rig_instance = get(node.ctl)
            rig_config = rig_instance.config()

        # -- Get the location of the control
        name_decomposition = rig_config.decompose_name(node.ctl)

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
    control_node = control.get(reference_node)
    rig = get(control_node.ctl)
    location_filter = control_node.location

    for node in all_controls():
        control_instance = control.get(node)
        if not control_instance:
            continue

        if control_instance.location == location_filter:
            filtered_controls.append(control_instance.ctl)

    return filtered_controls
