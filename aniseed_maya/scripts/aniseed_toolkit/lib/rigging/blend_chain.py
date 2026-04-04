import mref
from maya import cmds


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
        )

        parent = self.parent
        created_joints = []

        for idx in range(len(self.transforms_a)):

            transform_a = self.transforms_a[idx]
            transform_b = self.transforms_b[idx]

            # -- Create the joint
            cmds.select(clear=True)
            blend_joint = mref.get(cmds.joint())

            match_target = self.transforms_a[idx]
            if self.match_transforms:
                match_target = self.match_transforms[idx]

            blend_joint.set_parent(parent)
            blend_joint.match_to(match_target)

            cmds.parentConstraint(
                transform_a.full_name(),
                blend_joint.full_name(),
                maintainOffset=True,
            )
            constraint = mref.get(
                cmds.parentConstraint(
                    transform_b.full_name(),
                    blend_joint.full_name(),
                maintainOffset=True,
                )[0]
            )
            constraint.attr("interpType").set(2)  # Shortest
            print(constraint.weight_attributes(full_name=True))
            # -- Hook up the direct connection
            blend_attribute.connect(constraint.weight_attributes(full_name=True)[1])

            # -- Hook up the reverse connection
            reverse_node = mref.create("reverse")
            blend_attribute.connect(reverse_node.attr("inputX"))
            reverse_node.attr("outputX").connect(constraint.weight_attributes(full_name=True)[0])

            created_joints.append(blend_joint)
            parent = blend_joint

        self.blend_joints = mref.get(created_joints)
