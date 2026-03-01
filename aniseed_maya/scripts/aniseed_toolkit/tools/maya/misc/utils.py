import aniseed_toolkit
import maya.cmds as mc
import maya.api.OpenMaya as om


class GetNameTool(aniseed_toolkit.Tool):

    identifier = "MObject Name"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Misc"
    ]

    def run(self, mobject: om.MObject = None):
        """
        This will return the name of the MObject pointer

        Args:
            mobject: MObject pointer

        Returns:
            Name of the node
        """
        return aniseed_toolkit.mutils.get_name(mobject)


class GetObjectTool(aniseed_toolkit.Tool):

    identifier = "Get MObject"
    user_facing = False
    categories = [
        "Misc"
    ]

    def run(self, name: str = "") -> om.MFnDependencyNode:
        """
        Given the name of a node, this will return the MObject representation. This means
        we can track the node easily without having to worry about name changes.

        Args:
            name: Name of the node to get a pointer to

        Returns:
            MObject reference
        """
        return aniseed_toolkit.mutils.get_mobject(name)


class GetPathTool(aniseed_toolkit.Tool):

    identifier = "Get DagPath"
    user_facing = False

    def run(self, name: str = "") -> om.MDagPath:
        """
        This will return the name of the MObject pointer

        Args:
            name: Name of the node to resolve the dagpath for

        Returns:
            OpenMaya.DagPath
        """
        return aniseed_toolkit.mutils.get_dagpath(name)
