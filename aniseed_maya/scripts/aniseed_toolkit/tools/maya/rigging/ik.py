import qtility
import aniseed_toolkit
import maya.cmds as mc



class AlignBonesForIk(aniseed_toolkit.Tool):

    AXIS = ["x", "y", "z"]
    AXIS_LABELS = [
        "positive x",
        "negative x",
        "positive y",
        "negative y",
        "positive z",
        "negative z",
    ]

    identifier = 'Align Bones For Ik'
    classification = "Rigging"
    categories = [
        "Transforms",
    ]

    def run(
        self,
        root: str = "",
        tip: str = "",
        primary_axis: str = "",
        polevector_axis: str = "",
        retain_child_transforms: bool = None,
    ) -> None:
        """
        This will align the bones down the chain based on a specific facing axis and
        a specific up axis. All joints including the end joint will be aligned (the
        end joint taking its vector from the projection of the joint before it).

        Args:
            root: The joint to start aligning from
            tip: The end joint - only joints between these two will be affected
            primary_axis: The axis to align to ('Positive X', 'Negative Y', etc)
            polevector_axis: The axis to align to (same format as primary_axis)
            retain_child_transforms: Whether to keep (in worldspace) the same transform
                for any children that are not part of the chain

        Returns:
            None
        """

        pre_selection = mc.ls(sl=True)

        if not root and not len(mc.ls(sl=True)) == 2:
            print("You must provide a root or a selection")
            return None

        if not tip and not len(mc.ls(sl=True)) == 2:
            print("You must provide a tip or a selection")
            return None

        root = root or mc.ls(sl=True)[0]
        tip = tip or mc.ls(sl=True)[1]

        if not primary_axis:
            primary_axis = qtility.request.item(
                title="Forward Axis",
                message="Please select which axis is running along the bone",
                items=self.AXIS_LABELS,
                editable=False,
            )
            if not primary_axis:
                return None

        if not polevector_axis:
            forward_channel = primary_axis[-1]
            possible_vector_channels = [
                possibility
                for possibility in self.AXIS_LABELS
                if not possibility.endswith(forward_channel)
            ]

            polevector_axis = qtility.request.item(
                title="Polevector Axis",
                message="Select the axis the polevector should face down",
                items=possible_vector_channels,
                editable=False,
            )

            if not polevector_axis:
                return

        if retain_child_transforms is None:
            retain_child_transforms = qtility.request.confirmation(
                title="Retain child transforms",
                message="Do you want to retain the worldspace transforms of child bones (excluding twists)?"
            )

        # -- Now we have all the data we need, remove any pins
        pinned_joints = list()

        all_joints_in_chain = aniseed_toolkit.run("Get Joints Between", start=root, end=tip)

        for joint in all_joints_in_chain:
            if aniseed_toolkit.run("Is Pinned", joint):
                pinned_joints.append(joint)
                aniseed_toolkit.run("Remove Pins", [joint])

        try:
            joint_parent = mc.listRelatives(root, parent=True)[0]
        except (TypeError, IndexError):
            joint_parent = None

        aim_axis = self.get_aim_dir(primary_axis)
        upvector_axis = self.get_aim_dir(polevector_axis)
        inverted_upvector_axis = self.get_inverted_aim_dir(polevector_axis)

        actual_chain = aniseed_toolkit.run(
            "Get Joints Between",
            root,
            tip,
        )
        aniseed_toolkit.run(
            "Move Joint Orients to Rotation",
            actual_chain,
        )

        # -- Store any child transforms
        child_transforms = dict()
        twist_factors = dict()

        for idx, joint in enumerate(actual_chain):
            for child in mc.listRelatives(joint, children=True) or list():
                if child in actual_chain:
                    continue

                child_transforms[child] = mc.xform(
                    child,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                )

                if "Twist" in child and idx < len(actual_chain):
                    twist_factors[child] = aniseed_toolkit.run(
                        "Get Factor Between",
                        child,
                        joint,
                        actual_chain[idx + 1],
                    )

        replicated_joints = aniseed_toolkit.run(
            "Replicate Chain",
            root,
            tip,
            parent=None,
        )
        aniseed_toolkit.run(
            "Move Joint Orients to Rotation",
            replicated_joints
        )

        for idx, joint in enumerate(replicated_joints):
            try:
                mc.parent(
                    joint,
                    world=True,
                )

            except RuntimeError:
                pass

            aniseed_toolkit.run(
                "Move Joint Orients to Rotation",
                [joint],
            )

        for idx, joint in enumerate(replicated_joints[:-1]):

            # -- special case for the first one
            if idx == 0:
                cns = mc.aimConstraint(
                    replicated_joints[idx + 1],
                    joint,
                    worldUpType="object",
                    worldUpObject=replicated_joints[-1],
                    aimVector=aim_axis,
                    upVector=inverted_upvector_axis,
                    maintainOffset=False,
                )
                mc.delete(cns)
                continue

            cns = mc.aimConstraint(
                replicated_joints[idx + 1],
                joint,
                worldUpType="object",
                worldUpObject=replicated_joints[idx - 1],
                aimVector=aim_axis,
                upVector=inverted_upvector_axis,
                maintainOffset=False,
            )
            mc.delete(cns)

        # -- Re parent the joints before copying the data
        for idx, joint in enumerate(replicated_joints):

            if idx == 0:
                if joint_parent:
                    mc.parent(
                        joint,
                        joint_parent
                    )
                continue

            mc.parent(
                joint,
                replicated_joints[idx - 1],
            )

        aniseed_toolkit.run(
            "Move Joint Orients to Rotation",
            replicated_joints,
        )

        # -- Zero the last joints rotation
        for axis in self.AXIS:
            mc.setAttr(
                f"{replicated_joints[-1]}.rotate{axis.upper()}",
                0,
            )

        for idx in range(len(actual_chain)):
            aniseed_toolkit.run(
                "Copy Joint Attributes",
                from_this=replicated_joints[idx],
                to_this=actual_chain[idx],
            )

        if retain_child_transforms:
            for child, matrix in child_transforms.items():
                mc.xform(
                    child,
                    matrix=child_transforms[child],
                    worldSpace=True,
                )

        # -- Deal with twist joints
        for idx, joint in enumerate(actual_chain):

            for child in mc.listRelatives(joint, children=True) or list():

                if child in actual_chain:
                    continue

                # -- Skip anything that is not a twist
                if "twist" not in child.lower():
                    continue

                # -- If we dont have an additional joint to aim down, skip it
                if idx >= len(actual_chain):
                    continue

                # -- Position the node
                aniseed_toolkit.run(
                    "Position Between",
                    child,
                    actual_chain[idx],
                    actual_chain[idx + 1],
                    twist_factors[child],
                )

                for axis in self.AXIS:
                    mc.setAttr(f"{child}.r{axis.lower()}", 0)
                    mc.setAttr(f"{child}.jointOrient{axis.upper()}", 0)


        mc.delete(replicated_joints)

        aniseed_toolkit.run("Create Pins", pinned_joints)
        mc.select(pre_selection)

    @classmethod
    def get_aim_dir(cls, aim_label):
        aim_label = aim_label.lower()
        aim_dir = [0, 0, 0]

        # for idx in range(values):
        index = cls.AXIS.index(aim_label[-1])
        aim_dir[index] = 1 * -1 if "negative" in aim_label else 1

        return aim_dir

    @classmethod
    def get_inverted_aim_dir(cls, aim_label):
        return [
            v * -1
            for v in cls.get_aim_dir(aim_label)
        ]
