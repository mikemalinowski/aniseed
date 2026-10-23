import aniseed_toolkit
from maya import cmds


class CopyPoseTool(aniseed_toolkit.Tool):

    identifier = "Pose Copy"
    classification = "Animation"
    categories = [
        "Posing",
    ]

    POSES = []

    def run(self, nodes: list[str] or None = None):
        """
        This will store the current local space transform of the selected
        controls and store them.

        Args:
            nodes: List of nodes to store. If none are given then the
                selection will be used
        """
        nodes = nodes or cmds.ls(sl=True)
        CopyPoseTool.POSES = []

        for node in nodes:
            CopyPoseTool.POSES.append(
                cmds.xform(
                    node,
                    query=True,
                    matrix=True,
                ),
            )


class PastePoseTool(aniseed_toolkit.Tool):

    identifier = "Pose Paste"
    classification = "Animation"
    categories = [
        "Posing",
    ]

    def run(self, nodes: list[str] or None = None):
        """
        This will apply the previously stored local space transforms back to the
        given nodes, in the order they were copied.

        Args:
            nodes: Nodes to paste the pose onto. If none are given then the
                selection will be used
        """

        nodes = nodes or cmds.ls(sl=True)

        for idx, matrix in enumerate(CopyPoseTool.POSES):

            try:
                node = nodes[idx]

            except IndexError:
                return

            cmds.xform(
                node,
                matrix=CopyPoseTool.POSES[idx],
            )


class CopyWorldSpacePoseTool(aniseed_toolkit.Tool):
    identifier = "Pose Copy (WorldSpace)"
    classification = "Animation"
    categories = [
        "Posing",
    ]

    POSES = []

    def run(self, nodes: list[str] or None = None):
        """
        This will store the current world space transform of the selected
        controls and store them.

        Args:
            nodes: List of nodes to store. If none are given then the
                selection will be used
        """
        nodes = nodes or cmds.ls(sl=True)
        CopyWorldSpacePoseTool.POSES = []

        for node in nodes:
            CopyWorldSpacePoseTool.POSES.append(
                cmds.xform(
                    node,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
            )


class PasteWorldSpacePoseTool(aniseed_toolkit.Tool):

    identifier = "Pose Paste (WorldSpace)"
    classification = "Animation"
    categories = [
        "Posing",
    ]

    def run(self, nodes: list[str] or None = None):
        """
        This will apply the previously stored world space transforms back to the
        given nodes, in the order they were copied.

        Args:
            nodes: Nodes to paste the pose onto. If none are given then the
                selection will be used
        """

        nodes = nodes or cmds.ls(sl=True)

        for idx, matrix in enumerate(CopyWorldSpacePoseTool.POSES):

            try:
                node = nodes[idx]

            except IndexError:
                return

            cmds.xform(
                node,
                matrix=CopyWorldSpacePoseTool.POSES[idx],
                worldSpace=True,
            )
