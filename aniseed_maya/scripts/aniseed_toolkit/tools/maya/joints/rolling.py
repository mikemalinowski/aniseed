import aniseed
import aniseed_toolkit
import maya.cmds as mc


class RollJoints(aniseed_toolkit.Tool):

    identifier = "Roll Joints"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name == "joints":
            return aniseed.widgets.ObjectList()
        if keyword_name == "axis":
            return aniseed.widgets.ItemSelector(default_item="x", items=["x", "y", "z"])

    def run(self, joints: list[str] = None, axis="x", value=90) -> None:
        """
        Moves the rotations on the given joints to the joint orients
        attributes (zeroing the rotations).

        Args:
            joints: List of joints to move the rotation attributes for

        Returns:
            None
        """
        if isinstance(joints, str):
            joints = [joints]

        if not joints:
            joints = mc.ls(sl=True)

        if not joints:
            return

        mapped_joints = dict()

        # -- Create our mapping joints
        for joint in joints:

            mc.select(clear=True)
            transient_joint = mc.joint()
            mc.xform(
                transient_joint,
                worldSpace=True,
                matrix=mc.xform(
                    joint,
                    query=True,
                    worldSpace=True,
                    matrix=True,
                ),
            )
            aniseed_toolkit.run("Move Joint Rotations To Orients", joints=[transient_joint])
            mc.setAttr(f"{transient_joint}.rotate{axis.upper()}", value)

            # -- Now we need to get the matrix of all children whilst
            # -- we perform the match
            child_matrices = dict()
            for child in mc.listRelatives(joint, children=True) or list():
                child_matrices[child] = mc.xform(
                    child,
                    query=True,
                    worldSpace=True,
                    matrix=True,
                )

            # -- Perform the roll match
            mc.xform(
                joint,
                worldSpace=True,
                matrix=mc.xform(
                    transient_joint,
                    query=True,
                    worldSpace=True,
                    matrix=True,
                ),
            )

            for child, matrix in child_matrices.items():
                mc.xform(
                    child,
                    worldSpace=True,
                    matrix=matrix,
                )

            # -- Finally delete the transient
            mc.delete(transient_joint)

        mc.select(joints)
        return None
