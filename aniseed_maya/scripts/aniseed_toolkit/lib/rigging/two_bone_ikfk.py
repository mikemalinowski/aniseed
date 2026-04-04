import mref
import aniseed_toolkit
from maya import cmds


def create_two_bone_ikfk(
        parent,
        root_joint,
        end_joint,
        attribute_host,
        attribute_name,
        soft_ik=None,
        soft_ik_host=None,
        constrain=True,
    ):
    instance = TwoBoneIKFK(
        parent,
        root_joint,
        end_joint,
        attribute_host,
        attribute_name,
        soft_ik,
        soft_ik_host,
        constrain,
    )
    instance.create()
    return instance

class TwoBoneIKFK:

    def __init__(
            self,
            parent,
            root_joint,
            end_joint,
            attribute_host,
            attribute_name,
            soft_ik=None,
            soft_ik_host=None,
            constrain=True,
    ):
        # -- Store our input variables
        self.parent = mref.get(parent)
        self.root_joint = mref.get(root_joint)
        self.end_joint = mref.get(end_joint)
        self.attribute_host = mref.get(attribute_host)
        self.attribute_name = attribute_name
        self.apply_soft_ik = soft_ik
        self.soft_ik_host = mref.get(soft_ik_host) if soft_ik_host else None
        self.driven_joints = aniseed_toolkit.joints.get_between(
            self.root_joint.full_name(),
            self.end_joint.full_name(),
        )
        self.constrain = constrain

        # -- Declare our output variables
        self.org = None
        self.ik_chain = None
        self.fk_chain = None
        self.blend_chain = None
        self.ik_target = None
        self.ik_upvector = None
        self.soft_ik_root = None
        self.soft_ik_target = None

    def create(self):

        self.org = mref.create(
            "transform",
            name="ikfk_org",
            parent=self.parent,
        )
        self.create_fk()
        self.create_ik()
        self.create_blend()

    def create_ik(self):

        # -- Create the ik chain and move the rotations
        # -- to the orients
        self.ik_chain = mref.get(
            aniseed_toolkit.joints.replicate_chain(
                from_this=self.root_joint.full_name(),
                to_this=self.end_joint.full_name(),
                parent=self.org.full_name(),
            )
        )
        aniseed_toolkit.joints.move_rotations_to_orients(
            [
                joint.full_name()
                for joint in self.ik_chain
            ]
        )

        # -- Create our ik targets
        self.ik_target = mref.create("transform", name=self.unique_name("ik_target"), parent=self.org)
        self.ik_upvector = mref.create("transform", name=self.unique_name("ik_upvector"), parent=self.org)

        self.ik_target.match_to(self.ik_chain[-1])
        self.ik_upvector.match_to(self.ik_chain[1])

        for joint in self.ik_chain:
            cmds.joint(
                joint.full_name(),
                edit=True,
                oj="xyz",
                sao="ydown",
                ch=True,
                zso=True,
            )
            joint.rename(self.unique_name("ik"))

        # -- Setup the ik
        handle, _ = mref.get(
            cmds.ikHandle(
                startJoint=self.ik_chain[0].full_name(),
                endEffector=self.ik_chain[-1].full_name(),
                solver="ikRPsolver",
                priority=1,
            ),
        )
        handle.attr("visibility").set(False)
        handle.set_parent(self.ik_target)

        # -- Apply the pole vector
        cmds.poleVectorConstraint(
            self.ik_upvector.full_name(),
            handle.full_name(),
            weight=1,
        )

        # -- Constrain the rotation of the last joint
        cmds.parentConstraint(
            self.ik_target.full_name(),
            self.ik_chain[-1].full_name(),
            maintainOffset=True,
            skipTranslate=["x", "y", "z"],
        )

        if self.apply_soft_ik:
            self.apply_soft_ik_behaviour()

    def create_fk(self):

        self.fk_chain = mref.get(
            aniseed_toolkit.joints.replicate_chain(
                from_this=self.root_joint.full_name(),
                to_this=self.end_joint.full_name(),
                parent=self.org.full_name(),
            ),
        )
        for joint in self.fk_chain:
            joint.rename(self.unique_name("fk"))

    def create_blend(self):
        self.blend_chain = mref.get(
            aniseed_toolkit.rigging.create_blend_chain(
                parent=self.org.full_name(),
                transforms_a=self.ik_chain.full_names(),
                transforms_b=self.fk_chain.full_names(),
                attribute_host=self.attribute_host.full_name(),
                attribute_name=self.attribute_name,
                match_transforms=self.fk_chain.full_names(),
            ).blend_joints
        )

        for driven_joint, blend_joint in zip(self.driven_joints, self.blend_chain):
            blend_joint.rename(self.unique_name("nk"))
            if self.constrain:
                cmds.parentConstraint(
                    blend_joint.name(),
                    driven_joint,
                    maintainOffset=True,
                )

    def apply_soft_ik_behaviour(self):

        self.soft_ik_root = mref.create(
            "transform",
            name=self.unique_name("soft_ik_root"),
            parent=self.org.full_name(),
        )
        self.soft_ik_root.match_to(self.ik_chain[0])

        self.soft_ik_target = mref.create(
            "transform",
            name=self.unique_name("soft_ik_target"),
            parent=self.ik_target.full_name(),
        )
        self.soft_ik_target.match_to(self.ik_target)

        # -- Now create the actual soft ik setup
        aniseed_toolkit.rigging.create_two_bone_soft_ik(
            root=self.soft_ik_root.full_name(),
            target=self.soft_ik_target.full_name(),
            second_joint=self.ik_chain[-2].full_name(),
            third_joint=self.ik_chain[-1].full_name(),
            host=self.soft_ik_host.full_name(),
        )

    def unique_name(self, name):
        counter = 1
        proposed_name = name

        while cmds.objExists(proposed_name):
            counter += 1
            proposed_name = f"{name}{counter}"

        return proposed_name

    def all_nodes(self):
        return [
            self.ik_target,
            self.ik_upvector
        ] + self.fk_chain + self.ik_chain + self.blend_chain
