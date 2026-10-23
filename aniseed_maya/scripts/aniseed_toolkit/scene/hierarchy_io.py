"""
Serialising node hierarchies (typically joints) to and from dictionaries and
files.

Note on maya.cmds: the dataset is keyed by node names, and the names Maya
returns when nodes are created and renamed (which can be partial paths such as
"grp|joint1" when not unique) are what the functions return. mref resolves and
reports names differently, so this module stays on cmds.
"""
import json
import logging
import typing

from maya import cmds

from ..registry import tool
from . import mirror as _mirror

log = logging.getLogger(__name__)


SUPPORTED_TYPES = [
    "transform",
    "joint",
    "parentConstraint",
    "pointConstraint",
]


@tool(
    "Get Joint Writer Supported Types",
    classification="Rigging",
    categories=["Joints"],
)
def get_supported_io_types() -> list[str]:
    """
    This will return a list of supported node types which are supported in
    the joint writing tools.

    Returns:
        List of node types which are supported (the module level
        SUPPORTED_TYPES list itself, not a copy)
    """
    return SUPPORTED_TYPES


def hierarchy_to_dict(nodes: list[str]) -> dict:
    """
    This will store the given nodes and their attributes to a dictionary.

    For each node the name, type and parent (only if the parent is also
    one of the given nodes) are stored, along with the translate, rotate
    and scale values (plus jointOrient and radius for joints). Parent and
    point constraints are stored with the node they constrain and their
    first target, but only if that target is one of the given nodes.
    Nodes which do not exist are skipped.

    Args:
         nodes: List of nodes to serialise. Uses the selection if no nodes
            are given.

    Returns:
        dict of the dataset in the format supported by the joint writing
        tools, keyed by node name
    """
    nodes = nodes or cmds.ls(selection=True)
    return _create_dataset_from_nodes(nodes)


@tool(
    "Deserialise Nodes From Dict",
    classification="Rigging",
    categories=["Joints"],
    user_facing=False,
)
def dict_to_hierarchy(
        root_parent: str = "",
        dataset: typing.Dict = None,
        apply_names: bool = True,
        invert: bool = False,
        worldspace_root: bool = False,
) -> dict:
    """
    This will take a dictionary (in the format returned by hierarchy_to_dict)
    and generate nodes based on that description.

    Only joint and transform entries create nodes (constraint entries are
    ignored). The selection is cleared before each node is created.

    Args:
        root_parent: The node the newly created structure should reside under
        dataset: The dictionary of data
        apply_names: Whether to apply the names to the created nodes.
            Otherwise they keep Maya's default names (joint1, transform1...)
        invert: Whether translations should be inverted or not (useful when
            mirroring)
        worldspace_root: If true, the stored local values of each root
            node (one without a parent in the data) are applied as its
            world space matrix

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


def write_hierarchy_file(nodes: list[str], filepath: str) -> None:
    """
    This will take the given nodes and serialise them (in the format
    returned by hierarchy_to_dict) to a json file and save that json file
    to the given filepath.

    Args:
        nodes: List of nodes to serialise
        filepath: The filepath to save the json file

    Returns:
        None
    """
    with open(filepath, "w") as f:
        json.dump(
            _create_dataset_from_nodes(nodes),
            f,
            sort_keys=True,
            indent=4,
        )


def load_hierarchy_file(
        root_parent: str,
        filepath: str,
        apply_names=True,
        invert=False,
        worldspace_root=False,
):
    """
    This will parse the given json file and generate the structure defined within
    it (see dict_to_hierarchy).

    Args:
        root_parent: The node the newly created structure should reside under
        filepath: The absolute path to the json file
        apply_names: Whether to apply the names to the created nodes
        invert: Whether translations should be inverted or not (useful when
            mirroring)
        worldspace_root: If true, the stored local values of each root
            node are applied as its world space matrix

    Returns:
        Dictionary where the key is the name as defined in the data and the value
        is the created node

    Note: this never prompts the user - see ui.dialogs.load_hierarchy_file for
    the version which asks for anything not given.
    """
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
    """
    Builds the serialised dataset for the given nodes (see
    hierarchy_to_dict for the format).
    """
    all_node_data = dict()

    for node in nodes:

        try:
            node_type = cmds.nodeType(node)
        except RuntimeError:
            log.warning(f"Could not find {node}, it will not be serialised")
            continue

        parents = cmds.listRelatives(node, parent=True)
        parent = parents[0] if parents else None

        if parent not in nodes:
            parent = None

        item_data = dict(
            name=node,
            parent=parent,
            attributes=dict(),
            type=node_type,
            root_transform_data=dict(),
        )

        if node_type == "joint":

            item_data["radius"] = cmds.getAttr(f"{node}.radius")

            for type_ in ["translate", "rotate", "scale", "jointOrient"]:
                for axis in ["X", "Y", "Z"]:
                    item_data["attributes"][type_ + axis] = cmds.getAttr(
                        node + "." + type_ + axis,
                    )

        if node_type == "transform":

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
                continue

            # -- We wont save constraints to nodes outside of our save list
            if constrain_to not in nodes:
                continue

            item_data["constrain_this"] = cmds.listRelatives(node, parent=True)[0]
            item_data["constrain_to"] = constrain_to

        all_node_data[node] = item_data

    return all_node_data


# --------------------------------------------------------------------------------------
def _create_nodes_from_dataset(root_parent: str, dataset: typing.Dict, apply_names=True,
                               invert=False, worldspace_root=False):
    """
    Creates the joints and transforms described by the given dataset (in
    the format returned by hierarchy_to_dict), rebuilds their parenting and
    applies the stored attribute values. Entries of any other type are
    skipped.

    Args:
        root_parent: The node to parent the root nodes (those without a
            parent in the data) under. If empty they stay at the scene root.
        dataset: The dataset dictionary
        apply_names: Whether to rename the created nodes to the stored names
        invert: Whether to negate the translation of every created node
        worldspace_root: If true, the local matrix of each root node is
            reapplied as its world space matrix

    Returns:
        Dictionary where the key is the name entry in the data and the value
        is the created node
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

        generated_item_map[item_data["name"]] = created_item

    # -- Now set up the parenting and set the attributes
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
        _mirror.invert_translation(transforms=generated_item_map.values())

    return generated_item_map
