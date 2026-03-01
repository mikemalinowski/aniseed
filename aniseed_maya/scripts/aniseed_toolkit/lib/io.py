import json
import typing
import qtility
from maya import cmds

from . import mirror

SUPPORTED_TYPES = [
    "transform",
    "joint",
    "parentConstraint",
    "pointConstraint",
]


def get_supported_io_types() -> list[str]:
    """
    This will return a list of supported node types which are supported in
    the joint writing tools.

    Returns:
        List of node types which are supported
    """
    return SUPPORTED_TYPES


def hierarchy_to_dict(nodes: list[str]) -> dict:
    """
    This will store the given nodes and their attributes to a dictionary

    Args:
         nodes: List of nodes to serialise

    Returns:
        dict of the dataset in the format supported by the joint writing tools
    """
    nodes = nodes or cmds.ls(selection=True)
    return _create_dataset_from_nodes(nodes)


def dict_to_hierarchy(
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
    return _create_nodes_from_dataset(
        root_parent,
        dataset,
        apply_names,
        invert,
        worldspace_root,
    )


def write_hierarchy_file(nodes: list[str] = None, filepath: str = None) -> None:
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
        if not cmds.ls(selection=True):
            return

        nodes = cmds.ls(selection=True)

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


def load_hierarchy_file(
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
    if not root_parent:
        try:
            root_parent = cmds.ls(selection=True)[0]

        except IndexError:
            print("Could not resolve parent")
            return

    if not filepath:
        filepath = qtility.request.filepath(
            title="Save Joint File",
            filter_="*.json (*.json)",
            save=False,
            parent=None,
        )

    if not filepath:
        print("Could not resolve file")
        return

    with open(filepath, "r") as f:
        all_joint_data = json.load(f)

    return _create_nodes_from_dataset(
        root_parent=root_parent,
        dataset=all_joint_data,
        apply_names=apply_names,
        invert=invert,
        worldspace_root=worldspace_root,
    )


# --------------------------------------------------------------------------------------
def _create_dataset_from_nodes(nodes):
    all_node_data = dict()

    for node in nodes:
        node_type = cmds.nodeType(node)

        try:
            parent = cmds.listRelatives(node, parent=True)[0]

        except:
            parent = None

        if parent not in nodes:
            parent = None

        item_data = dict(
            name=node,
            parent=parent,
            attributes=dict(),
            type=cmds.nodeType(node),
            root_transform_data=dict(),
        )

        if node_type == "joint":

            item_data["radius"] = cmds.getAttr(f"{node}.radius")
            # item_data["root_transform_data"] = _get_root_transform_data(node)

            for type_ in ["translate", "rotate", "scale", "jointOrient"]:
                for axis in ["X", "Y", "Z"]:
                    item_data["attributes"][type_ + axis] = cmds.getAttr(
                        node + "." + type_ + axis,
                    )

        if node_type == "transform":

            # item_data["root_transform_data"] = _get_root_transform_data(node)

            for type_ in ["translate", "rotate", "scale"]:
                for axis in ["X", "Y", "Z"]:
                    item_data["attributes"][type_ + axis] = cmds.getAttr(
                        node + "." + type_ + axis,
                    )

        if node_type == "parentConstraint":

            try:
                constrain_to = cmds.parentConstraint(
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

            item_data["constrain_this"] = cmds.listRelatives(node, parent=True)[0]
            item_data["constrain_to"] = constrain_to

        if node_type == "pointConstraint":

            try:
                constrain_to = cmds.pointConstraint(
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

            item_data["constrain_this"] = cmds.listRelatives(node, parent=True)[0]
            item_data["constrain_to"] = constrain_to

        all_node_data[node] = item_data

    return all_node_data


# --------------------------------------------------------------------------------------
def _create_nodes_from_dataset(root_parent: str, dataset: typing.Dict, apply_names=True,
                               invert=False, worldspace_root=False):
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
        cmds.select(clear=True)

        item_type = item_data.get("type", "joint")
        created_item = None
        if item_type == "joint":
            created_item = cmds.joint()
            cmds.setAttr(created_item + ".radius", item_data.get("radius", 1))

        elif item_type == "transform":
            created_item = cmds.createNode("transform")

        # -- If it was an invalid type, then do nothing
        if not created_item:
            continue

        if apply_names:
            created_item = cmds.rename(
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
            cmds.parent(
                item,
                generated_item_map[parent_name]
            )

        elif root_parent:
            cmds.parent(
                item,
                root_parent,
            )
            root_nodes.append(identifier)

        for name, value in dataset[identifier]["attributes"].items():
            if cmds.objExists(item + "." + name):
                cmds.setAttr(item + "." + name, value)

    # -- Now check if we need to apply it in worldspace
    if worldspace_root:
        for identifier, item in generated_item_map.items():
            if not dataset[identifier]["parent"]:
                local_matrix = cmds.xform(item, query=True, matrix=True)
                cmds.xform(item, matrix=local_matrix, worldSpace=True)

    if invert:
        mirror.invert_translation(transforms=generated_item_map.values())

    return generated_item_map
