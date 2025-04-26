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


        if isinstance(mobject, str):
            return mobject

        try:
            return om.MFnDependencyNode(mobject).name()

        except ValueError:
            raise ValueError(f"Could not get dependency node for {mobject}")


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

        if isinstance(name, om.MObject):
            return name

        try:
            selection_list = om.MSelectionList()
            selection_list.add(name)

            return selection_list.getDependNode(0)

        except RuntimeError:
            raise RuntimeError(f"Could not find node {name}")


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
        if not mc.objExists(name):
            return None

        slist = om.MSelectionList()
        slist.add(name)

        return slist.getDagPath(0)
