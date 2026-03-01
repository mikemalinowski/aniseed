import typing
import aniseed
import aniseed_toolkit
import maya.cmds as mc


class JointWriterSupportedTypes(aniseed_toolkit.Tool):

    identifier = "Get Joint Writer Supported Types"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(self) -> list[str]:
        """
        This will return a list of supported node types which are supported in 
        the joint writing tools.
        
        Returns:
            List of node types which are supported
        """
        return aniseed_toolkit.io.get_supported_io_types()


class SerialiseNodesToDict(aniseed_toolkit.Tool):

    identifier = "Serialise Nodes To Dict"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Joints",
    ]

    def run(self, nodes: list[str]) -> dict:
        """
        This will store the given nodes and their attributes to a dictionary
        
        Args: 
             nodes: List of nodes to serialise
        
        Returns:
            dict of the dataset in the format supported by the joint writing tools
        """
        return aniseed_toolkit.io.hierarchy_to_dict(
            nodes=nodes or mc.ls(selection=True),
        )


class CreateNodesFromDict(aniseed_toolkit.Tool):

    identifier = "Deserialise Nodes From Dict"
    classification = "Rigging"
    user_facing = False
    categories = [
        "Joints",
    ]

    def run(
        self,
        root_parent: str = "",
        dataset: typing.Dict = None,
        apply_names: bool = True,
        invert: bool = False,
        worldspace_root: bool = False,
    ) -> dict:
        """
        This will take a dictionary (in the format returned by SerialiseNodesToDict)
        and generate nodes based on that description.
        
        Args:
            root_parent: The node the newly created structure should reside under
            dataset: The dictionary of data 
            apply_names: Whether to apply the names to the created nodes
            invert: Whether translations should be inverted or not (useful when
                mirroring)
            worldspace_root: If true, the values will be applied in worldspace
        
        Returns:
            Dictionary where the key is the name as defined in the data and the value
            is the created node            
        """
        return aniseed_toolkit.io.dict_to_hierarchy(
            root_parent=root_parent,
            dataset=dataset,
            apply_names=apply_names,
            invert=invert,
            worldspace_root=worldspace_root,
        )


class WriteJointFileTool(aniseed_toolkit.Tool):

    identifier = "Write Joints File"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(self, nodes: list[str] = None, filepath: str = None) -> None:
        """
        This will take the given nodes and serialise them to a json file
        and save that json file to the given filepath.
        
        Args: 
            nodes: List of nodes to serialise
            filepath: The filepath to save the json file
        
        Returns:
            None
        """
        return aniseed_toolkit.io.write_hierarchy_file(
            nodes=nodes,
            filepath=filepath,
        )


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
