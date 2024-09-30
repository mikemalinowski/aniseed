import traceback
import shapeshift
import maya.cmds as mc

from . import mutils


_STRUCTURE = [
    "org",
    "zro",
    "off",
    "ctl",
]


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def create(
    description: str,
    location: str,
    parent: str,
    shape: str,
    config: "aniseed.RigConfiguration",
    match_to: str = None,
    shape_scale: float = 1.0,
    rotate_shape=None,
    classification_override=None
) -> str:
    """
    This will create a control structure. It is not mandatory to use this within the
    rigging framework, but by doing so you will have a consistent behaviour with all
    components that come packaged with the rigging tool.
    """
    nodes = dict()
    next_parent = parent

    _structure = [
        config.organisational,
        config.zero,
        config.offset,
        config.control,
    ]

    for classification in _structure:

        nodes[classification] = mutils.get_object(
            mc.createNode("transform"),
        )

        name_classification = classification_override or classification

        mc.rename(
            mutils.get_name(nodes[classification]),
            config.generate_name(
                classification=name_classification,
                description=description,
                location=location,
            ),
        )

        if next_parent:
            mc.parent(
                mutils.get_name(nodes[classification]),
                next_parent,
            )

        mc.xform(
            mutils.get_name(nodes[classification]),
            matrix=mc.xform(
                match_to,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        next_parent = mutils.get_name(nodes[classification])

    # -- Apply the shape to the control
    shapeshift.apply(
        mutils.get_name(nodes[config.control]),
        shape,
    )

    if shape_scale != 1.0:
        shapeshift.scale(
            mutils.get_name(nodes[config.control]),
            shape_scale
        )

    if rotate_shape:
        shapeshift.rotate_shape(
            mutils.get_name(nodes[config.control]),
            x=rotate_shape[0],
            y=rotate_shape[1],
            z=rotate_shape[2],
        )

    # -- Attach the networking
    for source_node_type in nodes:
        for target_node_type in nodes:

            if source_node_type == target_node_type:
                continue

            source_node = mutils.get_name(nodes[source_node_type])
            target_node = mutils.get_name(nodes[target_node_type])

            mc.addAttr(
                source_node,
                shortName=f"link_{target_node_type}",
                at="message",
            )

            mc.connectAttr(
                f"{target_node}.message",
                f"{source_node}.link_{target_node_type}"
            )

    controller_name = mutils.get_name(nodes["ctl"])

    mc.addAttr(
        controller_name,
        shortName="location",
        dt="string",
    )

    mc.setAttr(
        f"{controller_name}.location",
        location,
        type="string",
    )
    mc.controller(
        controller_name,
    )

    return controller_name


# --------------------------------------------------------------------------------------
def get_location(controller: str) -> str:
    """
    Returns the location tag of the control
    """
    if mc.objExists(f"{controller}.location"):
        return mc.getAttr(f"{controller}.location")

    return ""


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def get_classification(node: str, component_type: str) -> str or None:
    """
    Returns the part of a control as defined by the component_type, such as the offset,
    zero or org etc.
    """
    attr = f"{node}.link_{component_type}"

    if not mc.objExists(attr):
        print(f"{attr} does not exist")
        return None

    try:
        return mc.listConnections(
            attr,
        )[0]

    except (ValueError, IndexError):
        print(f"Failed to get component")
        traceback.print_exc()
        return None


# --------------------------------------------------------------------------------------
def basic_transform(classification, description, location, config, parent=None, match_to=None):
    # -- Create our component org to keep everything together
    node = mc.rename(
        mc.createNode("transform"),
        config.generate_name(
            classification=classification,
            description=description,
            location=location,
        ),
    )

    if parent:
        mc.parent(
            node,
            parent,
        )

    mc.xform(
        node,
        matrix=mc.xform(
            match_to,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    return node
