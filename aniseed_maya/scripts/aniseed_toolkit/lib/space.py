import uuid

import mref
from . import control


def add_space_switch(component, label: str, driven: str, default_space: str, spaces: list[tuple[str, str]]):
    """
    Adds a Space Switch component as a child of the given component. The
    driven node also hosts the space switch attribute.

    Args:
        component: The component to add the space switch beneath
        label: The label for the space switch component
        driven: The address of the node to be driven
        default_space: The label of the space which should be active by default
        spaces: List of (label, target address) tuples, in the order they
            should appear

    Returns:
        The space switch component
    """
    space_switch = component.stack.add_component(
        component_type="Augment : Space Switch",
        label=label,
        parent=component,
        inputs={
            "To Be Driven": driven,
            "Attribute Host": driven,
        },
    )
    space_switch.option("_Data").set(
        {
            "default_space": default_space,
            "spaces": [
                {
                    "target": target,
                    "position_only": False,
                    "orientation_only": False,
                    "target_transform": "",
                    "label": space_label,
                    "include_scale": True,
                    "uuid_": str(uuid.uuid4()),
                }
                for space_label, target in spaces
            ]
        }
    )
    return space_switch


def setup_fk_worldspace_switches(nodes, rig):
    """
    Adds an orientation space switch to each of the given fk controls,
    allowing them to switch between following their parent and the world.
    """
    _setup_fk_switches(nodes, rig, orientation_only=True, default_space="Parent")


def setup_fk_transform_worldspace_switches(nodes, rig, default_space="Parent"):
    """
    Adds a full transform space switch to each of the given fk controls,
    allowing them to switch between following their parent and the world.
    """
    _setup_fk_switches(nodes, rig, orientation_only=False, default_space=default_space)


def _setup_fk_switches(nodes, rig, orientation_only: bool, default_space: str):
    nodes = [mref.get(node) for node in nodes]

    # -- The first node's space parent is whatever its control sits under,
    # -- after that, each node's parent space is the previous node
    parent = mref.get(control.get(nodes[0].name()).org).parent()
    world = get_root_control()

    for node in nodes:

        data = {
            "default_space": default_space,
            "spaces": [
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
            ]
        }

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
