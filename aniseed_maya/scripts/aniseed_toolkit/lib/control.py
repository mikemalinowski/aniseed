import json
import traceback
import aniseed
import aniseed_toolkit
from maya import cmds

from . import shapes


class Control:
    """
    The control class ensures that you can easily access the org, offset, zero and
    control parts which make up a typical aniseed control hierarchy.
    """

    def __init__(self, node: str):
        self._control_node = node

    @property
    def ctl(self) -> str:
        """
        Returns the control part of the control hierarchy
        """
        return self.part("ctl")

    @property
    def org(self) -> str:
        """
        Returns the org node (the top node of the control hierarchy)
        """
        return self.part("org")

    @property
    def off(self) -> str:
        """
        Returns the offset node of the control hierarchy (useful when applying
        constraints or driven attributes)
        """
        return self.part("off")

    @property
    def zero(self) -> str:
        """
        Returns the zero node of the control hierarchy
        """
        return self.part("zro")

    @property
    def location(self):
        """
        Returns the location tag of the control
        """
        if cmds.objExists(f"{self._control_node}.naming_data"):
            return json.loads(cmds.getAttr(f"{self._control_node}.naming_data"))["location"]
        return ""

    def part(self, classification: str) -> str or None:
        """
        This will attempt to look at the structure of the control hierarchy
        and return the part based on the given classification.
        """
        attr = f"{self._control_node}.link_{classification}"

        if not cmds.objExists(attr):
            return self._control_node

        try:
            return cmds.listConnections(
                attr,
            )[0]

        except (ValueError, IndexError):
            print(f"Failed to get component")
            traceback.print_exc()
            return None

    @classmethod
    def get(cls, node: str) -> "Control" or None:
        """
        This will attempt to instance a Control class for the given node
        """
        attr = f"{node}.link_ctl"

        if not cmds.objExists(attr):
            return Control(node)

        try:
            return Control(
                cmds.listConnections(
                    attr,
                )[0],
            )

        except (ValueError, IndexError):
            print(f"Failed to get component")
            traceback.print_exc()
            return None

    @classmethod
    def create(
            cls,
            description: str,
            location: str,
            parent: str,
            shape: str,
            config: "aniseed.RigConfiguration",
            match_to: str = None,
            shape_scale: float = 1.0,
            rotate_shape=None,
            classification_override=None
    ) -> "Control":
        """
        This will create a control structure. It is not mandatory to use this within the
        rigging framework, but by doing so you will have a consistent behaviour with all
        components that come packaged with the rigging tool.

        Args:
            description (str): Descriptive part of the nodes name
            location (str): Location of the control
            parent (str): Parent of the control
            shape (str): Shape of the control to apply (should be accessible via
                aniseed_toolkit/_resources/shapes
            config: The rig configuration instance
            match_to: Optional object to match transform to
            shape_scale: Scale of the shape to apply to the control, default is 1.0
            rotate_shape: Optional object to rotate shape to apply to the control, default is None
            classification_override: By default this will always use the control
                prefix as per the rig configuration, but you can specify an override.

        Returns:
            Control: The created control which has an accessor for the zero,
                offset, and org node which makes up a controls hierarchy.
        """
        nodes = dict()
        next_parent = parent

        _structure = {
            config.organisational: "org",
            config.zero: "zro",
            config.offset: "off",
            config.control: "ctl",
        }

        for classification in _structure:

            nodes[classification] = aniseed_toolkit.run("Get MObject",
                cmds.createNode("transform"),
            )

            name_classification = classification_override or classification

            cmds.rename(
                aniseed_toolkit.run("MObject Name", nodes[classification]),
                config.generate_name(
                    classification=name_classification,
                    description=description,
                    location=location,
                ),
            )

            if next_parent:
                cmds.parent(
                    aniseed_toolkit.run("MObject Name", nodes[classification]),
                    next_parent,
                )

            cmds.xform(
                aniseed_toolkit.run("MObject Name", nodes[classification]),
                matrix=cmds.xform(
                    match_to,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            next_parent = aniseed_toolkit.run("MObject Name", nodes[classification])

        control_name = aniseed_toolkit.run("MObject Name", nodes[config.control])
        cmds.setAttr(
            f"{control_name}.visibility",
            # lock=True,
            keyable=False,
        )

        # -- Apply the shape to the control
        aniseed_toolkit.run(
            "Apply Shape",
            control_name,
            shape,
        )

        if shape_scale != 1.0:
            aniseed_toolkit.run(
                "Scale Shapes",
                control_name,
                shape_scale
            )

        if rotate_shape:
            shapes.rotate(
                control_name,
                x=rotate_shape[0],
                y=rotate_shape[1],
                z=rotate_shape[2],
            )

        # -- Attach the networking
        for source_node_type in nodes:
            for target_node_type in nodes:

                if source_node_type == target_node_type:
                    continue

                source_node = aniseed_toolkit.run("MObject Name", nodes[source_node_type])
                target_node = aniseed_toolkit.run("MObject Name", nodes[target_node_type])

                cmds.addAttr(
                    source_node,
                    shortName=f"link_{_structure[target_node_type]}",
                    attributeType="message",
                )

                cmds.connectAttr(
                    f"{target_node}.message",
                    f"{source_node}.link_{_structure[target_node_type]}"
                )

        controller_name = aniseed_toolkit.run("MObject Name", nodes[config.control])

        cmds.addAttr(
            controller_name,
            shortName="naming_data",
            dataType="string",
        )

        cmds.setAttr(
            f"{controller_name}.naming_data",
            json.dumps(
                dict(
                    classification=config.control,
                    location=location,
                    description=description,
                )
            ),
            type="string",
        )
        cmds.controller(
            controller_name,
        )

        return Control(controller_name)


def create(
        description: str = "",
        location: str = "",
        parent: str = "",
        shape: str = "",
        config: "aniseed.RigConfiguration" = None,
        match_to: str = None,
        shape_scale: float = 1.0,
        rotate_shape=None,
        classification_override=None
) -> "Control":
    """
    This will create a control structure. It is not mandatory to use this within the
    rigging framework, but by doing so you will have a consistent behaviour with all
    components that come packaged with the rigging tool.

    Args:
        description (str): Descriptive part of the nodes name
        location (str): Location of the control
        parent (str): Parent of the control
        shape (str): Shape of the control to apply (should be accessible via
            aniseed_toolkit/_resources/shapes
        config: The rig configuration instance
        match_to: Optional object to match transform to
        shape_scale: Scale of the shape to apply to the control, default is 1.0
        rotate_shape: Optional object to rotate shape to apply to the control, default is None
        classification_override: By default this will always use the control
            prefix as per the rig configuration, but you can specify an override.

    Returns:
        Control: The created control which has an accessor for the zero,
            offset, and org node which makes up a controls hierarchy.
    """
    return Control.create(
        description=description,
        location=location,
        parent=parent,
        shape=shape,
        config=config,
        match_to=match_to,
        shape_scale=shape_scale,
        rotate_shape=rotate_shape,
        classification_override=classification_override,
    )


def get(node: str) -> Control:
    """
    This will instance a Control class for the given node

    Args:
        node: The node to instance a control class for (it can be any part of a
            control hierarchy, but MUST be part of a valid control hierarchy).

    Returns:
        Control instance
    """
    return Control.get(node)


def set_as_zero_transform(node: str) -> None:

    # -- Get the node as a control object
    control = aniseed_toolkit.run("Get Control", node)

    # -- Read the world transform
    world_xform = cmds.xform(
        control.ctl,
        query=True,
        matrix=True,
        worldSpace=True,
    )

    # -- We need to reset all of these in this specific order
    items = [
        control.org,
        control.zero,
        control.off,
        control.ctl,
    ]

    for item in items:
        cmds.xform(
            item,
            matrix=world_xform,
            worldSpace=True,
        )
