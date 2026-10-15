"""
JointChainMixin, for components which drive a joint chain defined by a root
and a tip input (with optional twist joints and guides). It provides the joint
and guide accessors along with removal and mirroring behaviour.
"""
import mref

from aniseed import builders as _builders
from aniseed_toolkit.scene import joints as _joints


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

        _builders.mirror_component(
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
