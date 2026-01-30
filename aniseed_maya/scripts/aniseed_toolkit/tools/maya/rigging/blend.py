import aniseed_toolkit
import maya.cmds as mc


class CreateBlendChain(aniseed_toolkit.Tool):

    identifier = "Create Blend Chain"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, parent, transforms_a, transforms_b, attribute_host, attribute_name, match_transforms=None):

        blend_chain = BlendChain(
            parent,
            transforms_a,
            transforms_b,
            attribute_host,
            attribute_name,
            match_transforms=match_transforms,
        )
        blend_chain.create()
        return blend_chain


class BlendChain:

    def __init__(self, parent, transforms_a, transforms_b, attribute_host, attribute_name, match_transforms=None):
        self.in_parent = parent
        self.in_transforms_a = transforms_a
        self.in_transforms_b = transforms_b
        self.in_attribute_host = attribute_host
        self.in_attribute_name = attribute_name
        self.in_match_transforms = match_transforms

        self._m_out_blend_joints = []

    @property
    def out_blend_joints(self):
        return [
            aniseed_toolkit.run("MObject Name", m_object)
            for m_object in self._m_out_blend_joints
        ]

    @out_blend_joints.setter
    def out_blend_joints(self, value):
        self._m_out_blend_joints = [
            aniseed_toolkit.run("Get MObject", name)
            for name in value
        ]


    def create(self):

        if len(self.in_transforms_a) != len(self.in_transforms_b):
            raise Exception("Transforms need to have the same length")

        # -- Add the attribute to the host
        mc.addAttr(
            self.in_attribute_host,
            shortName=self.in_attribute_name,
            at="float",
            dv=0,
            k=True,
            min=0,
            max=1,
        )
        attribute_address = f"{self.in_attribute_host}.{self.in_attribute_name}"

        # -- Determine the first parent
        parent = self.in_parent
        blend_joints = []

        # -- Now cycle the transforms
        for idx in range(len(self.in_transforms_a)):

            # -- Create the blend joint
            mc.select(clear=True)
            blend_joint = mc.joint()

            match_target = self.in_transforms_a[idx]
            if self.in_match_transforms:
                match_target = self.in_match_transforms[idx]

            mc.parent(
                blend_joint,
                parent,
            )

            mc.xform(
                blend_joint,
                matrix=mc.xform(
                    match_target,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            # -- Create the constraint between the two items
            mc.parentConstraint(
                self.in_transforms_a[idx],
                blend_joint,
                maintainOffset=True,
            )
            cns = mc.parentConstraint(
                self.in_transforms_b[idx],
                blend_joint,
                maintainOffset=True,
            )[0]
            mc.setAttr(
                f"{cns}.interpType",
                2,  # -- Shortest
            )

            # -- Get the alias attributes
            constraint_attributes = [
                f"{cns}.{alias}"
                for alias in mc.parentConstraint(cns, q=True, weightAliasList=True)
            ]

            # -- Hook up the attribute to the constraints
            mc.connectAttr(
                attribute_address,
                constraint_attributes[1],
            )

            reverse_node = mc.createNode("reverse")
            mc.connectAttr(
                attribute_address,
                f"{reverse_node}.inputX",
            )
            mc.connectAttr(
                f"{reverse_node}.outputX",
                constraint_attributes[0],
            )

            blend_joints.append(blend_joint)
            parent = blend_joint

        self.out_blend_joints = blend_joints





