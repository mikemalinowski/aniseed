import typing
import aniseed
import aniseed_toolkit
import maya.cmds as mc


class LoadJointFileTool(aniseed_toolkit.Tool):

    identifier = "Load Joints File"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name == "root_parent":
            return aniseed.widgets.ObjectSelector()
        if keyword_name == "filepath":
            return aniseed.widgets.FilepathSelector()
        
    def run(
        self,
        root_parent: str = "",
        filepath: str = "",
        apply_names=True,
        invert=False,
        worldspace_root=False,
    ):
        """
        This will parse the given json file and generate the structure defined within
        it.
        
        Args:
            root_parent: The node the newly created structure should reside under
            filepath: The absolute path to the json file
            apply_names: Whether to apply the names to the created nodes
            invert: Whether translations should be inverted or not (useful when
                mirroring)
            worldspace_root: If false, the root of the structure will be matched
                in worldspace
        
        Returns:
            Dictionary where the key is the name as defined in the data and the value
            is the created node 
        """
        return aniseed_toolkit.io.load_hierarchy_file(
            root_parent=root_parent,
            filepath=filepath,
            apply_names=apply_names,
            invert=invert,
            worldspace_root=worldspace_root,
        )
