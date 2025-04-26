
import json
import typing
import qtility
import aniseed_toolkit
import maya.cmds as mc

SUPPORTED_TYPES = [
    "transform",
    "joint",
    "parentConstraint",
    "pointConstraint",
]


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
        return SUPPORTED_TYPES


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
        return _create_dataset_from_nodes(nodes)


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
        localise_root: bool = False,
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
            localise_root: If false, the root of the structure will be matched
                in worldspace
        
        Returns:
            Dictionary where the key is the name as defined in the data and the value
            is the created node            
        """
        return _create_nodes_from_dataset(
            root_parent,
            dataset,
            apply_names,
            invert,
            localise_root,
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
        if not nodes:
            if not mc.ls(sl=True):
                return

            joints = mc.ls(sl=True)

        if not filepath:
            filepath = qtility.request.filepath(
                title="Save Joint File",
                filter_="*.json (*.json)",
                save=True,
                parent=None,
            )

        if not filepath:
            return

        with open(filepath, "w") as f:
            json.dump(
                _create_dataset_from_nodes(nodes),
                f,
                sort_keys=True,
                indent=4,
            )


class LoadJointFileTool(aniseed_toolkit.Tool):

    identifier = "Load Joints File"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(
        self,
        root_parent=None,
        filepath=None,
        apply_names=True,
        invert=False,
        localise_root=False,
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
            localise_root: If false, the root of the structure will be matched
                in worldspace
        
        Returns:
            Dictionary where the key is the name as defined in the data and the value
            is the created node 
        """
        if not root_parent:
            try:
                root_parent = mc.ls(sl=True)[0]

            except IndexError:
                return

        if not filepath:
            filepath = qtility.request.filepath(
                title="Save Joint File",
                filter_="*.json (*.json)",
                save=False,
                parent=None,
            )

        if not filepath:
            return

        with open(filepath, "r") as f:
            all_joint_data = json.load(f)

        return _create_nodes_from_dataset(
            root_parent=root_parent,
            dataset=all_joint_data,
            apply_names=apply_names,
            invert=invert,
            localise_root=localise_root,
        )


# --------------------------------------------------------------------------------------
def _create_dataset_from_nodes(nodes):
    all_node_data = dict()

    for node in nodes:
        node_type = mc.nodeType(node)

        try:
            parent = mc.listRelatives(node, parent=True)[0]

        except:
            parent = None

        if parent not in nodes:
            parent = None


        item_data = dict(
            name=node,
            parent=parent,
            attributes=dict(),
            type=mc.nodeType(node),
            root_transform_data=dict(),
        )

        if node_type == "joint":

            item_data["radius"] = mc.getAttr(f"{node}.radius")
            item_data["root_transform_data"] = _get_root_transform_data(node)

            for type_ in ["translate", "rotate", "scale", "jointOrient"]:
                for axis in ["X", "Y", "Z"]:
                    item_data["attributes"][type_ + axis] = mc.getAttr(
                        node + "." + type_ + axis,
                    )

        if node_type == "transform":

            item_data["root_transform_data"] = _get_root_transform_data(node)

            for type_ in ["translate", "rotate", "scale"]:
                for axis in ["X", "Y", "Z"]:
                    item_data["attributes"][type_ + axis] = mc.getAttr(
                        node + "." + type_ + axis,
                    )

        if node_type == "parentConstraint":

            try:
                constrain_to = mc.parentConstraint(
                    node,
                    query=True,
                    targetList=True,
                )[0]

            except IndexError:
                # -- We cannot get the constraint output, so skip
                continue

            # -- We wont save constraints to nodes outside of our save list
            if constrain_to not in nodes:
                continue

            item_data["constrain_this"] = mc.listRelatives(node, parent=True)[0]
            item_data["constrain_to"] = constrain_to

        if node_type == "pointConstraint":

            try:
                constrain_to = mc.pointConstraint(
                    node,
                    query=True,
                    targetList=True,
                )[0]

            except IndexError:
                # -- We cannot get the constraint output, so skip
                print("Could not get constraint target")
                continue

            # -- We wont save constraints to nodes outside of our save list
            if constrain_to not in nodes:
                print(f"{constrain_to} does not exist")
                continue

            item_data["constrain_this"] = mc.listRelatives(node, parent=True)[0]
            item_data["constrain_to"] = constrain_to

        all_node_data[node] = item_data

    return all_node_data

# --------------------------------------------------------------------------------------
def _get_root_transform_data(node):

    try:
        parent = mc.listRelatives(node, parent=True)[0]

        parent_translation = mc.xform(
            parent,
            query=True,
            translation=True,
            worldSpace=True,
        )

    except IndexError:
        parent_translation = [0, 0, 0]

    node_ws_translation = mc.xform(
        node,
            query=True,
            translation=True,
            worldSpace=True,
    )

    relative_translation = [
        node_ws_translation[0] - parent_translation[0],
        node_ws_translation[1] - parent_translation[1],
        node_ws_translation[2] - parent_translation[2],
    ]

    return dict(
        relative_translation=relative_translation,
        ws_orientation=mc.xform(node, query=True, ws=True, rotation=True),
    )

# --------------------------------------------------------------------------------------
def _apply_root_transform_data(node, data):

    print("applying root transform data")
    try:
        parent = mc.listRelatives(node, parent=True)[0]

        parent_translation = mc.xform(
            parent,
            query=True,
            translation=True,
            worldSpace=True,
        )

    except IndexError:
        parent_translation = [0, 0, 0]

    mc.xform(
        node,
        translation=[
            parent_translation[0] + data["relative_translation"][0],
            parent_translation[1] + data["relative_translation"][1],
            parent_translation[2] + data["relative_translation"][2],
        ],
        worldSpace=True,
    )

    mc.xform(
        node,
        rotation=data["ws_orientation"],
        worldSpace=True,
    )

# --------------------------------------------------------------------------------------
def _create_nodes_from_dataset(root_parent: str, dataset: typing.Dict, apply_names=True, invert=False, localise_root=False):
    """
    Creates a joint hierarchy based on the given data. If the data
    is a dictionary it is parsed as is otherwise it is assumed to be
    a json file and will be read accordingly.

    :param root_parent: The joint in which to parent the generated
        structure under.
    :type root_parent: pm.nt.Joint

    :param dataset: Either a dictionary conforming to the structure
        generated by the write_joint_file method or a filepath to a json file
        containing the equivalent structure.
    :type dataset: dict or str

    :return: dictionary where the key is the name entry in the file
        and the value is the generated joint
    """
    generated_item_map = dict()

    for item_data in dataset.values():

        # -- Create the joint
        mc.select(clear=True)

        item_type = item_data.get("type", "joint")
        created_item = None
        if item_type == "joint":
            created_item = mc.joint()
            mc.setAttr(created_item + ".radius", item_data.get("radius", 1))

        elif item_type == "transform":
            created_item = mc.createNode("transform")

        # -- If it was an invalid type, then do nothing
        if not created_item:
            continue

        if apply_names:
            created_item = mc.rename(
                created_item,
                item_data["name"]
            )

        # -- Set the joint attributes
        generated_item_map[item_data["name"]] = created_item

    root_nodes = []

    # -- Now set up the parenting
    for identifier, item in generated_item_map.items():

        parent_name = dataset[identifier]["parent"]

        if parent_name:
            mc.parent(
                item,
                generated_item_map[parent_name]
            )

        elif root_parent:
            mc.parent(
                item,
                root_parent,
            )
            root_nodes.append(identifier)

        for name, value in dataset[identifier]["attributes"].items():
            if mc.objExists(item + "." + name):
                mc.setAttr(item + "." + name, value)

    if not localise_root:
        print("setting special")
        for identifier in root_nodes:

            # -- If there is no root transform data, do nothing
            if "root_transform_data" not in dataset[identifier]:
                print("no root transform data")
                continue

            root_data = dataset[identifier]["root_transform_data"]
            node = generated_item_map[identifier]

            _apply_root_transform_data(node, root_data)

    # -- Always do constraints last
    for item_data in dataset.values():
        if item_data.get("type") == "parentConstraint":
            created_item = mc.parentConstraint(
                item_data["constrain_to"],
                item_data["constrain_this"],
                maintainOffset=True
            )

        if item_data.get("type") == "pointConstraint":
            created_item = mc.pointConstraint(
                item_data["constrain_to"],
                item_data["constrain_this"],
                maintainOffset=True
            )
    if invert:
        aniseed_toolkit.run("Invert Translation", transforms=generated_item_map.values())

    return generated_item_map
