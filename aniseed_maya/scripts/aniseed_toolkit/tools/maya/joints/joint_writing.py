import typing
import aniseed
import aniseed_toolkit
import aniseed_toolkit.ui.dialogs
from maya import cmds


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
            worldspace_root: If true, the stored local values of each root node
                are applied as its world space matrix
        
        Returns:
            Dictionary where the key is the name as defined in the data and the value
            is the created node 
        """
        return aniseed_toolkit.ui.dialogs.load_hierarchy_file(
            root_parent=root_parent,
            filepath=filepath,
            apply_names=apply_names,
            invert=invert,
            worldspace_root=worldspace_root,
        )


@aniseed_toolkit.tool(
    "Serialise Nodes To Dict",
    classification="Rigging",
    categories=["Joints"],
    user_facing=False,
)
def serialise_nodes_to_dict(nodes: list[str]) -> dict:
    """
    This will store the given nodes and their attributes to a dictionary
    
    Args: 
         nodes: List of nodes to serialise
    
    Returns:
        dict of the dataset in the format supported by the joint writing tools
    """
    return aniseed_toolkit.scene.hierarchy_io.hierarchy_to_dict(
        nodes=nodes or cmds.ls(selection=True),
    )


@aniseed_toolkit.tool(
    "Write Joints File",
    classification="Rigging",
    categories=["Joints"],
)
def write_joints_file(nodes: list[str] = None, filepath: str = None) -> None:
    """
    This will take the given nodes (or the selection) and serialise them to a
    json file, asking for the filepath if one is not given.

    Args:
        nodes: List of nodes to serialise
        filepath: The filepath to save the json file

    Returns:
        None
    """
    return aniseed_toolkit.ui.dialogs.write_hierarchy_file(nodes, filepath)