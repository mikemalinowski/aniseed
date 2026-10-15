"""
Blend chains: joint chains which blend between two sets of transforms (such
as an ik and an fk chain) driven by a single attribute.
"""
from maya import cmds
import mref

from ..scene import constraints as _constraints


def create_blend_chain(
        parent,
        transforms_a,
        transforms_b,
        attribute_host,
        attribute_name,
        match_transforms=None,
    ):
    instance = BlendChain(
        parent,
        transforms_a,
        transforms_b,
        attribute_host,
        attribute_name,
        match_transforms,
    )
    instance.create()
    return instance


class BlendChain:
    """
    Creates a chain of joints which are blended between two sets of
    transforms by a 0-1 attribute (where 0 is fully transforms_a and 1 is
    fully transforms_b).
    """

    def __init__(
            self,
            parent,
            transforms_a,
            transforms_b,
            attribute_host,
            attribute_name,
            match_transforms=None,
    ):
        # -- Get references to our inputs
        self.parent = mref.get(parent)
        self.transforms_a = mref.get(transforms_a)
        self.transforms_b = mref.get(transforms_b)
        self.attribute_host = mref.get(attribute_host)
        self.attribute_name = attribute_name
        self.match_transforms = mref.get(match_transforms) if match_transforms else None

        # -- Now declare our outputs
        self.blend_joints = None

    def create(self):
        # -- Start by validating
        if len(self.transforms_a) != len(self.transforms_b):
            raise Exception("Transforms need to match")

        blend_attribute = self.attribute_host.add_attribute(
            name=self.attribute_name,
            value=0,
            attribute_type="float",
            min=0,
            max=1,
            keyable=True,
        )

        parent = self.parent
        created_joints = []

        for idx, (transform_a, transform_b) in enumerate(zip(self.transforms_a, self.transforms_b)):

            # -- Create the joint. The selection is cleared so the joint
            # -- is not created under whatever is selected (cmds is used
            # -- as mref.select does not support clearing)
            cmds.select(clear=True)
            blend_joint = mref.get(mref.joint())

            match_target = self.match_transforms[idx] if self.match_transforms else transform_a

            blend_joint.set_parent(parent)
            blend_joint.match_to(match_target)

            mref.parentConstraint(
                transform_a,
                blend_joint,
                maintainOffset=True,
            )
            constraint = mref.parentConstraint(
                transform_b,
                blend_joint,
                maintainOffset=True,
            )[0]
            constraint.attr("interpType").set(2)  # Shortest

            _constraints.blend_weights(blend_attribute, constraint)

            created_joints.append(blend_joint)
            parent = blend_joint

        self.blend_joints = mref.get(created_joints)
