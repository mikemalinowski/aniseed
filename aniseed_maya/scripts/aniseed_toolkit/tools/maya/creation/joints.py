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
        return aniseed_toolkit.joints.create(
            description=description,
            location=location,
            parent=parent,
            config=config,
            match_to=match_to,
        )


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
        return aniseed_toolkit.joints.create_spread(
            root_joint=root_joint,
            tip_joint=tip_joint,
            joint_count=joint_count,
            axis=axis,
            naming_function=naming_function,
        )
