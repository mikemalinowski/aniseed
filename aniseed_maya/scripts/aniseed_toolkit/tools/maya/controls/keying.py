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
    
    identifier = "Snap IKFK"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]
    
    def run(self, nodes=None):

        # -- Get the nodes
        nodes = nodes or cmds.ls(selection=True)

        # -- Read the time range
        playback_slider = maya.mel.eval("$tmp = $gPlayBackSlider")
        time_range = cmds.timeControl(playback_slider, query=True, rangeArray=True)
        start_frame = int(time_range[0])
        end_frame = int(time_range[1])

        # -- Get the groups for all the nodes
        groups = []
        for node in cmds.ls(selection=True):
            groups.extend(snappy.groups(node))
        groups = list(set(groups))

        for group in groups:
            snappy.snap(group=group, start_time=start_frame, end_time=end_frame)