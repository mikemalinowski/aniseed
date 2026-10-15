import qtility
import aniseed_toolkit
import maya.cmds as mc



class AlignBonesForIk(aniseed_toolkit.Tool):

    AXIS = aniseed_toolkit.rigging.bone_alignment.AXIS
    AXIS_LABELS = aniseed_toolkit.rigging.bone_alignment.AXIS_LABELS

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

        aniseed_toolkit.rigging.bone_alignment.align_bones_for_ik(
            root=root,
            tip=tip,
            primary_axis=primary_axis,
            polevector_axis=polevector_axis,
            retain_child_transforms=retain_child_transforms,
        )

        mc.select(pre_selection)

    @classmethod
    def get_aim_dir(cls, aim_label):
        return aniseed_toolkit.rigging.bone_alignment.get_aim_dir(aim_label)

    @classmethod
    def get_inverted_aim_dir(cls, aim_label):
        return aniseed_toolkit.rigging.bone_alignment.get_inverted_aim_dir(aim_label)
