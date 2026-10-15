import mref
import qtility

from . import shapes
from . import joints as _joints
from . import mirror as _mirror


def mirror(component_instance, transforms, location_label, config, joint_parent=None, input_overrides=None, option_overrides=None):
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
            shapes.rotate(
                twist,
                *shape_rotation,
            )

    return twist_component


def request_count(count, title: str, message: str) -> int:
    """
    Returns the given count, or if it is None, asks the user for it.
    """
    if count is None:
        count = int(qtility.request.text(title=title, message=message))
    return count


class JointChainMixin:
    """
    Mixin for components which drive a joint chain defined by a root and a
    tip input, optionally with twist joint inputs and guide inputs. It
    provides the joint/guide accessors and the removal and mirroring
    behaviour.

    Compose alongside RigComponent, mixin first:

        class Arm(aniseed_toolkit.component.JointChainMixin, aniseed.RigComponent):
            chain_root_input = "Shoulder"
            chain_tip_input = "Hand"
    """

    # -- The names of the inputs which define the joint chain
    chain_root_input = ""
    chain_tip_input = ""

    # -- The names of the list inputs holding twist joints
    chain_twist_inputs = [
        "Upper Twist Joints",
        "Lower Twist Joints",
    ]

    # -- The tags of the guides, each held in a "<tag> Guide" input
    guide_tags = []

    # -- Whether removing the component should also delete the guides
    delete_guides_on_removal = False

    # -- Whether the guides should be mirrored along with the joints
    mirror_guides = False

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we remove its joints,
        re-parenting any children which do not belong to the component.
        """
        root_joint = self.input(self.chain_root_input).get()

        new_parent = mref.get(root_joint).parent()
        _joints.reparent_unknown_children(self.all_joints(), new_parent)

        mref.delete(root_joint)

        if self.delete_guides_on_removal:
            mref.delete(self.all_guides())

    def user_func_create_mirror(self):
        """
        This will create a mirrored version of the component
        """
        transforms = self.all_joints()
        if self.mirror_guides:
            transforms = self.all_guides() + transforms

        mirror(
            component_instance=self,
            transforms=transforms,
            location_label="Location",
            config=self.config,
            joint_parent=mref.get(self.input(self.chain_root_input).get()).parent().name(),
            input_overrides={self.chain_root_input: ""},
        )

    def all_joints(self):
        """
        Returns all the joints this component affects
        """
        root_joint = self.input(self.chain_root_input).get()
        tip_joint = self.input(self.chain_tip_input).get()

        if not mref.objExists(root_joint) or not mref.objExists(tip_joint):
            return []

        all_joints = _joints.get_between(root_joint, tip_joint)

        for input_name in self.chain_twist_inputs:
            all_joints += self.input(input_name).get() or []

        return [joint for joint in all_joints if joint]

    def all_guides(self):
        """
        Returns the guide transforms for this component
        """
        return [
            self.input(f"{guide_tag} Guide").get()
            for guide_tag in self.guide_tags
        ]
