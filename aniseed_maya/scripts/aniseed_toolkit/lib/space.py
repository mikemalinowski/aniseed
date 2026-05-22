import mref
import maya.cmds as cmds
from . import control


def setup_fk_worldspace_switches(nodes, rig):

    # -- get the world control
    pass

    nodes = [mref.get(node) for node in nodes]
    # -- Parent
    parent = mref.get(control.get(nodes[0].name()).org).parent()
    world = get_root_control()

    for node in nodes:

        data = {
            "default_space": "Parent",
            "spaces": [
                {
                    "target": parent.name(),
                    "position_only": False,
                    "orientation_only": True,
                    "target_transform": "",
                    "label": "Parent",
                    "include_scale": False,
                },
                {
                    "target": world,
                    "position_only": False,
                    "orientation_only": True,
                    "target_transform": "",
                    "label": "World",
                    "include_scale": False,
                }
            ]
        }
        print(data)
        # -- Add a space switch on this node with the default being the parent
        # -- and the alternate being the world.
        space_switch_component = rig.component_library.request("Augment : Space Switch")(label="", stack=rig)

        space_switch_component.input("To Be Driven").set(node.name())
        space_switch_component.input("Attribute Host").set(node.name())

        space_switch_component.option("_Data").set(data)
        space_switch_component.run()

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
    for tag in cmds.ls(type='controller') or []:
        objs = cmds.listConnections(
            tag + ".controllerObject",
            s=True,
            d=False
        ) or []

        controls.update(objs)

    # --- Fallback naming convention ---
    controls.update(cmds.ls('*_CTRL', type='transform') or [])

    if not controls:
        return None

    def hierarchy_depth(node):
        """
        Computes DAG depth from full path.
        Example:
            |root|grp|ctrl  -> depth 3
        """
        path = cmds.ls(node, long=True)[0]
        return path.count('|')

    shallowest = min(controls, key=hierarchy_depth)

    return shallowest
