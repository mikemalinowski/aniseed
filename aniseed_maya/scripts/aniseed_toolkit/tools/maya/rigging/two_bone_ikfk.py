"""
import maya.cmds as mc
import aniseed_toolkit

aniseed_toolkit.run(
    "Create Two Bone IKFK",
    root_joint="joint1",
    mid_joint="joint2",
    end_joint="joint3",
    attribute_host="null1",
    attribute_name="ikfk",

)
"""
import aniseed_toolkit
import maya.cmds as mc


class CreateTwoBoneIKFK(aniseed_toolkit.Tool):

    identifier = "Create Two Bone IKFK"
    classification = "Rigging"
    categories = [
        "Rigging",
    ]

    def run(
        self,
        parent,
        root_joint,
        end_joint,
        attribute_host,
        attribute_name,
        constrain=True,
        soft_ik=True,
    ):
        ikfk_setup = TwoBoneIKFK(
            parent,
            root_joint,
            end_joint,
            attribute_host,
            attribute_name,
            constrain,
            soft_ik,
        )
        ikfk_setup.create()
        return ikfk_setup


class TwoBoneIKFK:

    def __init__(self, parent, root_joint, end_joint,  attribute_host, attribute_name, constrain=True, soft_ik=True):

        # -- Store the incoming joints
        self.in_parent = parent
        self.in_root_joint = root_joint
        self.in_end_joint = end_joint
        self.in_attribute_host = attribute_host
        self.in_attribute_name = attribute_name

        # -- Store the build parameters
        self.constrain = constrain
        self.soft_ik = soft_ik

        # -- Output variables
        self._out_m_org = None
        self._out_m_ik_chain = None
        self._out_m_fk_chain = None
        self._out_m_blend_chain = None
        self._out_m_ik_target = None
        self._out_m_ik_upvector = None
        self._out_m_softik_root = None
        self._out_m_softik_target = None

    @property
    def out_blend_joints(self):
        return [
            aniseed_toolkit.run("MObject Name", m_object)
            for m_object in self._out_m_blend_chain
        ]

    @out_blend_joints.setter
    def out_blend_joints(self, value):
        self._out_m_blend_chain = [
            aniseed_toolkit.run("Get MObject", name)
            for name in value
        ]

    @property
    def out_ik_joints(self):
        return [
            aniseed_toolkit.run("MObject Name", m_object)
            for m_object in self._out_m_ik_chain
        ]

    @out_ik_joints.setter
    def out_ik_joints(self, value):
        self._out_m_ik_chain = [
            aniseed_toolkit.run("Get MObject", name)
            for name in value
        ]

    @property
    def out_fk_joints(self):
        return [
            aniseed_toolkit.run("MObject Name", m_object)
            for m_object in self._out_m_fk_chain
        ]

    @out_fk_joints.setter
    def out_fk_joints(self, value):
        self._out_m_fk_chain = [
            aniseed_toolkit.run("Get MObject", name)
            for name in value
        ]

    @property
    def out_ik_target(self):
        return aniseed_toolkit.run("MObject Name", self._out_m_ik_target)

    @out_ik_target.setter
    def out_ik_target(self, value):
        self._out_m_ik_target = aniseed_toolkit.run("Get MObject", value)

    @property
    def out_ik_upvector(self):
        return aniseed_toolkit.run("MObject Name", self._out_m_ik_upvector)

    @out_ik_upvector.setter
    def out_ik_upvector(self, value):
        self._out_m_ik_upvector = aniseed_toolkit.run("Get MObject", value)

    @property
    def out_org(self):
        return aniseed_toolkit.run("MObject Name", self._out_m_org)

    @out_org.setter
    def out_org(self, value):
        self._out_m_org = aniseed_toolkit.run("Get MObject", value)

    @property
    def out_sofk_ik_root(self):
        return aniseed_toolkit.run("MObject Name", self._out_m_softik_root)

    @out_sofk_ik_root.setter
    def out_sofk_ik_root(self, value):
        self._out_m_softik_root = aniseed_toolkit.run("Get MObject", value)

    @property
    def out_sofk_ik_target(self):
        return aniseed_toolkit.run("MObject Name", self._out_m_softik_target)

    @out_sofk_ik_target.setter
    def out_sofk_ik_target(self, value):
        self._out_m_softik_target = aniseed_toolkit.run("Get MObject", value)

    @property
    def all_nodes(self):
        nodes = []
        nodes.extend(self.out_ik_joints)
        nodes.extend(self.out_fk_joints)
        nodes.extend(self.out_blend_joints)
        nodes.append(self.out_ik_target)
        nodes.append(self.out_ik_upvector)
        nodes.append(self.out_org)
        return nodes
    
    def create(self):
        pass

        self.out_org = mc.createNode(
            "transform",
            name="IKFKOrg",
        )

        if self.in_parent:
            mc.parent(
                self.out_org,
                self.in_parent,
            )

        self.create_fk()
        self.create_ik()
        self.create_blend()

    def create_ik(self):

        self.out_ik_joints = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.in_root_joint,
            to_this=self.in_end_joint,
            parent=self.out_org,
        )

        # -- Move joint rotations to orients
        aniseed_toolkit.run(
            "Move Joint Rotations To Orients",
            joints=self.out_ik_joints,
        )

        # -- Create the ik targets
        self.out_ik_target = mc.createNode("transform", name="ik_target")
        self.out_ik_upvector = mc.createNode("transform", name="ik_upvector")

        mc.parent(
            self.out_ik_target,
            self.out_org,
        )
        mc.parent(
            self.out_ik_upvector,
            self.out_org,
        )

        mc.xform(
            self.out_ik_target,
            m=mc.xform(
                self.out_ik_joints[-1],
                q=True,
                m=True,
                ws=True,
            ),
            ws=True,
        )
        mc.xform(
            self.out_ik_upvector,
            m=mc.xform(
                self.out_ik_joints[1],
                q=True,
                m=True,
                ws=True,
            ),
            ws=True,
        )

        for joint in self.out_ik_joints:
            mc.joint(
                joint,
                edit=True,
                oj="xyz",
                sao="ydown",
                ch=True,
                zso=True,
            )
            mc.rename(
                joint,
                self.unique_name("ik"),
            )

        # -- Setup the ik handle
        handle, effector = mc.ikHandle(
            startJoint=self.out_ik_joints[0],
            endEffector=self.out_ik_joints[-1],
            solver='ikRPsolver',
            priority=1,
        )
        mc.setAttr(
            f"{handle}.visibility",
            0,
        )
        mc.parent(
            handle,
            self.out_ik_target,
        )
        # -- Apply the upvector constraint
        mc.poleVectorConstraint(
            self.out_ik_upvector,
            handle,
            weight=1,
        )

        # -- Constrain the rotation of the last joint
        mc.parentConstraint(
            self.out_ik_target,
            self.out_ik_joints[-1],
            maintainOffset=True,
            skipTranslate=["x", "y", "z"],
        )

        if self.soft_ik:
            self.apply_soft_ik()

    def create_fk(self):

        self.out_fk_joints = aniseed_toolkit.run(
            "Replicate Chain",
            from_this=self.in_root_joint,
            to_this=self.in_end_joint,
            parent=self.out_org,
        )
        for joint in self.out_fk_joints:
            mc.rename(
                joint,
                self.unique_name("fk"),
            )


    def create_blend(self):

        blend_chain = aniseed_toolkit.run(
            "Create Blend Chain",
            parent=self.out_org,
            transforms_a=self.out_ik_joints,
            transforms_b=self.out_fk_joints,
            attribute_host=self.in_attribute_host,
            attribute_name=self.in_attribute_name,
            match_transforms=self.out_fk_joints,
        )
        self.out_blend_joints = blend_chain.out_blend_joints

        driven_joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.in_root_joint,
            self.in_end_joint,
        )

        for idx, joint in enumerate(self.out_blend_joints):

            if self.constrain:
                mc.parentConstraint(
                    joint,
                    driven_joints[idx],
                    maintainOffset=True,
                )

            mc.rename(
                joint,
                self.unique_name("nk"),
            )

    def apply_soft_ik(self):

        self.out_sofk_ik_root = mc.createNode("transform", name=self.unique_name("soft_ik_root"))

        mc.parent(
            self.out_sofk_ik_root,
            self.out_org,
        )

        mc.xform(
            self.out_sofk_ik_root,
            matrix=mc.xform(
                self.out_ik_joints[0],
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        self.out_sofk_ik_target = mc.createNode("transform", name=self.unique_name("soft_ik_target"))

        mc.parent(
            self.out_sofk_ik_target,
            self.out_ik_target,
        )

        mc.xform(
            self.out_sofk_ik_target,
            matrix=mc.xform(
                self.out_ik_joints[-1],
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        aniseed_toolkit.run(
            "Create Soft Ik",
            root=self.out_sofk_ik_root,
            target=self.out_sofk_ik_target,
            second_joint=self.out_ik_joints[-2],
            third_joint=self.out_ik_joints[-1],
            host=self.in_attribute_host,
        )

    def unique_name(self, name):
        counter = 1
        proposed_name = name

        while mc.objExists(proposed_name):
            counter += 1
            proposed_name = f"{name}{counter}"

        return proposed_name
