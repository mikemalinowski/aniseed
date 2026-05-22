import mref
import aniseed_toolkit
import snappy
import maya
from maya import cmds


class KeyRigControls(aniseed_toolkit.Tool):

    identifier = "Key All Rig Controls"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]

    def run(self):
        """
        This will key all the controls of the currently selected rig(s). If no
        rig is selected then it will key all controls for all rigs.
        """
        cmds.setKeyframe(
            aniseed_toolkit.run(
                "Get Controls",
            ),
        )


class SnapIKFK(aniseed_toolkit.Tool):
    
    identifier = "Snap IKFK (Selected Limb)"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]
    
    def run(self, nodes=None):
        # -- Get the groups for all the nodes
        groups = []
        for node in nodes or cmds.ls(selection=True):
            groups.extend(snappy.groups(node))
        groups = list(set(groups))

        start_time = None
        end_time = None

        if mref.time.selected_number_of_frames() > 1:
            start_time = mref.time.selected_start_frame()
            end_time = mref.time.selected_end_frame()

        for group in groups:
            if "IKFK" in group:
                snappy.snap(
                    group=group,
                    start_time=start_time,
                    end_time=end_time,
                )


class SnapIKFKInRig(aniseed_toolkit.Tool):
    identifier = "Snap IKFK (All In Rig)"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]

    def run(self, namespace=None):

        if not namespace and cmds.ls(selection=True):
            namespace = cmds.ls(selection=True)[0].split(":")[0]

        if not namespace:
            return

        start_time = None
        end_time = None
        if mref.time.selected_number_of_frames() > 1:
            start_time = mref.time.selected_start_frame()
            end_time = mref.time.selected_end_frame()

        # -- Get the groups for all the nodes
        for group in snappy.groups_in_namespace(namespace):
            if "IKFK" in group:
                snappy.snap(
                    group=group,
                    start_time=start_time,
                    end_time=end_time,
                )

