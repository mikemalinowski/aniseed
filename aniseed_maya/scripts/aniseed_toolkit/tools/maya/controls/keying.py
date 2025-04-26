import aniseed_toolkit
import maya.cmds as mc


class KeyRigControls(aniseed_toolkit.Tool):

    identifer = "Key Rig Controls"
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
        mc.setKeyframe(
            aniseed_toolkit.run(
                "Get Controls",
            ),
        )
