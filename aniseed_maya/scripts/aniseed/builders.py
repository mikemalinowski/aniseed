"""
Helpers which build aniseed components programmatically on behalf of other
components: space switches, fk world space switches, twisters, mirrored
components and joints created under the current selection.
"""
import uuid

import mref

from aniseed_toolkit.rig import control as _control
from aniseed_toolkit.scene import mirror as _mirror
from aniseed_toolkit.scene import shapes as _shapes
from aniseed_toolkit.rig import space as _space


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
    parent = mref.get(_control.get(nodes[0].name()).org).parent()
    world = _space.get_root_control()

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


def mirror_component(component_instance, transforms, location_label, config, joint_parent=None, input_overrides=None, option_overrides=None):
    original_location = component_instance.option(location_label).get()

    if original_location not in [config.left, config.right]:
        print("You can only mirror if the component is left or right")
        return

    # -- Get the opposite location
    new_location = config.left if original_location == config.right else config.right

    # -- Select the parent joint and duplicate ourselves (setting hte label so
    # -- we know its mirrored. Note that we clear the root bone as this will
    # -- trigger the duplcated component to generate the skeleton too.
    if joint_parent:
        mref.select(joint_parent)

    option_overrides = option_overrides or dict()
    option_overrides.update({location_label: new_location})

    mirrored_component = component_instance.duplicate(
        input_overrides=input_overrides or dict(),
        option_overrides=option_overrides,
    )
    mirrored_component.set_label(f"{component_instance.label()} (Mirrored)")

    # -- Now we do an in-place mirror
    _mirror.global_mirror(
        transforms=transforms,
        name_replacement=[
            config.resolved_location(original_location),
            config.resolved_location(new_location),
        ],
    )


def add_twister(rig, joints, parent, root, tip, prefix, location, shape_rotation=None):
    """
    Builds an "Augment : Twister" component (outside of the stack) to drive
    the given twist joints between the root and the tip. The twist root is
    left unconstrained whilst the tip is constrained to the tip driver.

    Args:
        rig: The rig the twister is being built for
        joints: The twist joints to drive
        parent: The node to parent the twist setup under
        root: The node driving the root of the twist
        tip: The node driving the tip of the twist
        prefix: The descriptive prefix for the twist setup
        location: The location for the twist setup
        shape_rotation: Optional x, y, z rotation to apply to the shapes
            of all the twist controls

    Returns:
        The twister component
    """
    twist_component = rig.component_library.request("Augment : Twister")(
        "",
        stack=rig,
    )

    twist_component.input("Joints").set(joints)
    twist_component.input("Parent").set(parent)
    twist_component.input("Root").set(root)
    twist_component.input("Tip").set(tip)

    twist_component.option("Constrain Root").set(False)
    twist_component.option("Constrain Tip").set(True)
    twist_component.option("Descriptive Prefix").set(prefix)
    twist_component.option("Location").set(location)

    twist_component.run()

    if shape_rotation is not None:
        for twist in twist_component.builder.all_controls():
            _shapes.rotate(
                twist,
                *shape_rotation,
            )

    return twist_component


def create_joint_from_selection(name: str, match_to_parent: bool = False) -> mref.ReferencedItem:
    """
    Creates a joint as a child of the first selected node, or at the world
    if nothing is selected.

    Args:
        name: The name to give the joint
        match_to_parent: If True, the joint is matched to the world
            transform of its parent

    Returns:
        The created joint
    """
    selection = mref.selected()
    parent = selection[0] if selection else None

    joint = mref.create("joint", parent=parent)
    joint.rename(name)

    if parent and match_to_parent:
        joint.match_to(parent)

    return joint
