import qute
import json
import typing
import itertools
import maya.cmds as mc

from . import flip

SUPPORTED_TYPES = [
    "transform",
    "joint",
    "parentConstraint",
    "pointConstraint",
]

# --------------------------------------------------------------------------------------
def write_joints_to_file(joints=None, filepath=None):

    if not joints:
        if not mc.ls(sl=True):
            return

        joints = mc.ls(sl=True)

    if not filepath:
        filepath = qute.utilities.request.filepath(
            title="Save Joint File",
            filter_="*.json (*.json)",
            save=True,
            parent=None,
        )

    if not filepath:
        return

    with open(filepath, "w") as f:
        json.dump(
            create_dataset_from_nodes(joints),
            f,
            sort_keys=True,
            indent=4,
        )


# --------------------------------------------------------------------------------------
def load_joints_from_file(root_parent=None, filepath=None, apply_names=True, invert=False, localise_root=False):

    if not filepath:
        filepath = qute.utilities.request.filepath(
            title="Save Joint File",
            filter_="*.json (*.json)",
            save=False,
            parent=None,
        )

    if not filepath:
        return

    with open(filepath, "r") as f:
        all_joint_data = json.load(f)

    return create_nodes_from_dataset(
        root_parent=root_parent,
        dataset=all_joint_data,
        apply_names=apply_names,
        invert=invert,
        localise_root=localise_root,
    )


# --------------------------------------------------------------------------------------
def create_dataset_from_nodes(nodes):
    """
    Writes out joint information to a json file to allow the joint
    structure to be rebuilt easily.

    :param joints: List of joints to write out
    :type joints: list(pm.nt.Joint, ...)

    :param filepath: Filepath to write to
    :type filepath: str

    :return: None
    """
    all_node_data = dict()

    for node in nodes:
        print(f"Creating data for {node} X")
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
def create_nodes_from_dataset(root_parent: str, dataset: typing.Dict, apply_names=True, invert=False, localise_root=False):
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
        flip.invert(transforms=generated_item_map.values())

    return generated_item_map
