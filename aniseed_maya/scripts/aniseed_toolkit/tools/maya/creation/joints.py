import aniseed_toolkit
import maya.cmds as mc


class CreateJoint(aniseed_toolkit.Tool):

    identifier = "Create Joint"
    classification = "Rigging"
    user_facing = False

    def run(
        self,
        description: str,
        location: str,
        parent: str,
        config: "aniseed.RigConfiguration",
        match_to: str = None,
    ):
        """
        This is a simple tool which creates a joint but sets up the name based on the
        aniseed configuration.

        Args:
            description: The descriptive part of the name to apply
            location: The location to apply the name to
            parent: The parent of the joint
            config: The aniseed configuration
            match_to: If given, the joint will have its transform matched
                to this node
        """
        mc.select(clear=True)

        joint_ = mc.joint()

        joint_ = mc.rename(
            joint_,
            config.generate_name(
                classification=config.joint,
                description=description,
                location=location,
            ),
        )

        if parent:
            mc.parent(
                joint_,
                parent,
            )

        if match_to:
            mc.xform(
                joint_,
                matrix=mc.xform(
                    match_to,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

        return joint_


class CreateSpreadJoints(aniseed_toolkit.Tool):

    identifier = "Create Spread Joints"
    classification = "Rigging"
    user_facing = False

    def run(
        self,
        root_joint: str,
        tip_joint: str,
        joint_count: float,
        axis="X",
        naming_function: callable = None,
    ):

        created_joints = []

        upper_increment = mc.getAttr(
            f"{tip_joint}.translate{axis.upper()}",
        ) / (joint_count - 1)

        upper_twist_joints = list()

        for idx in range(joint_count):
            mc.select(clear=True)
            spread_joint = mc.rename(mc.joint(), "SpreadJoint")

            if naming_function:
                spread_joint = mc.rename(spread_joint, naming_function())

            mc.parent(
                spread_joint,
                root_joint,
            )

            mc.xform(
                spread_joint,
                matrix=mc.xform(
                    root_joint,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            mc.setAttr(
                f"{spread_joint}.translateX",
                upper_increment * idx
            )

            created_joints.append(spread_joint)

        return created_joints
