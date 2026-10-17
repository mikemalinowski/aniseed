"""
Controls: the Control class (which gives access to the org, zero, offset and
ctl parts of a control hierarchy), control creation, offset controls and
queries for controls with curve shapes.
"""
import json
import traceback
import typing

from maya import cmds
import mref

from ..registry import tool
from ..core._nodes import resolve as _resolve
from ..scene import shapes as _shapes

if typing.TYPE_CHECKING:
    import aniseed



class Control:
    """
    The control class ensures that you can easily access the org, offset, zero and
    control parts which make up a typical aniseed control hierarchy.

    Every part is returned as a node name (str), exactly as maya reports it.

    Args:
        node: The control node (the ctl part) of the hierarchy. Use
            Control.get to instance the class from any part of a hierarchy.
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
    def location(self) -> str:
        """
        Returns the location stored in the control's naming_data attribute,
        or an empty string if the control has no naming_data.
        """
        address = f"{self._control_node}.naming_data"
        if mref.objExists(address):
            return json.loads(_resolve(address).get())["location"]
        return ""

    def part(self, classification: str) -> str or None:
        """
        Returns the part of the control hierarchy with the given
        classification, by following the link_<classification> attribute.

        Args:
            classification: One of "org", "zro", "off" or "ctl"

        Returns:
            The name of the part. If the node has no such link attribute
            (i.e. it is not part of a control hierarchy) the node itself is
            returned. None is returned if the link attribute has no
            connection.
        """
        attr = f"{self._control_node}.link_{classification}"

        if not mref.objExists(attr):
            return self._control_node

        # -- cmds rather than mref, as the part is returned as the name
        # -- maya reports (which may be a partial path if it is not unique)
        try:
            return cmds.listConnections(
                attr,
            )[0]

        except (ValueError, IndexError):
            print("Failed to get component")
            traceback.print_exc()
            return None

    @classmethod
    def get(cls, node: str) -> "Control" or None:
        """
        Instances a Control class for the given node, which can be any part
        of a control hierarchy.

        Args:
            node: Any part of a control hierarchy. If the node is not part
                of a control hierarchy it is used as the control node itself.

        Returns:
            The Control instance, or None if the hierarchy link is broken.
        """
        attr = f"{node}.link_ctl"

        if not mref.objExists(attr):
            return Control(node)

        # -- cmds rather than mref, as the Control stores the node name
        # -- maya reports
        try:
            return Control(
                cmds.listConnections(
                    attr,
                )[0],
            )

        except (ValueError, IndexError):
            print("Failed to get component")
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
            classification_override=None,
            counter=1
    ) -> "Control":
        """
        This will create a control structure (org, zero, offset and ctl
        transforms, each parented under the previous one). It is not mandatory
        to use this within the rigging framework, but by doing so you will have
        a consistent behaviour with all components that come packaged with the
        rigging tool.

        Every part is linked to every other part through link_<part> message
        attributes, the ctl is given a naming_data attribute and is tagged as
        a controller.

        Args:
            description (str): Descriptive part of the nodes name
            location (str): Location of the control
            parent (str): Parent of the control. If empty, the control is
                created at the scene root.
            shape (str): Shape of the control to apply (should be accessible via
                aniseed_toolkit/_resources/shapes). If empty no shape is applied.
            config: The rig configuration instance
            match_to: Optional object to match transform to. If not given,
                the nodes keep the world transform they were created with (the origin).
            shape_scale: Scale of the shape to apply to the control, default is 1.0
            rotate_shape: Optional x, y, z rotation to apply to the shape,
                default is None
            classification_override: By default this will always use the control
                prefix as per the rig configuration, but you can specify an override.
            counter: The counter to use when generating the names, default is 1

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

            node = mref.create("transform")
            node.rename(
                config.generate_name(
                    classification=classification_override or classification,
                    description=description,
                    location=location,
                    counter=counter,
                ),
            )

            if next_parent:
                node.set_parent(next_parent)

            # -- Without a match_to the node is matched to its own world
            # -- matrix. This is a deliberate re-application which keeps the
            # -- output identical to when this was resolved from the selection.
            match_target = mref.get(match_to) if match_to else node
            node.set_matrix(match_target.get_matrix(space="world"), space="world")

            nodes[classification] = node
            next_parent = node

        control = nodes[config.control]
        control.attr("visibility").set(keyable=False)

        # -- Apply the shape to the control
        if shape:
            _shapes.load_shape(control.name(), shape)

        if shape_scale != 1.0:
            _shapes.scale(control.name(), scale_by=shape_scale)

        if rotate_shape:
            _shapes.rotate(
                control.name(),
                x=rotate_shape[0],
                y=rotate_shape[1],
                z=rotate_shape[2],
            )

        # -- Link every part of the control hierarchy to every other part
        for source_classification, source_node in nodes.items():
            for target_classification, target_node in nodes.items():

                if source_classification == target_classification:
                    continue

                link = source_node.add_attribute(
                    f"link_{_structure[target_classification]}",
                    value=None,
                    attribute_type="message",
                )
                target_node.attr("message").connect(link)

        control.add_attribute(
            "naming_data",
            value=json.dumps(
                dict(
                    classification=config.control,
                    location=location,
                    description=description,
                )
            ),
            attribute_type="string",
        )
        mref.controller(control)

        return Control(control.name())


def create(
        description: str = "",
        location: str = "",
        parent: str = "",
        shape: str = "",
        config: "aniseed.RigConfiguration" = None,
        match_to: str = None,
        shape_scale: float = 1.0,
        rotate_shape=None,
        classification_override=None,
        counter=1,
) -> "Control":
    """
    This will create a control structure. It is not mandatory to use this within the
    rigging framework, but by doing so you will have a consistent behaviour with all
    components that come packaged with the rigging tool. See Control.create for
    the structure which is built.

    Args:
        description (str): Descriptive part of the nodes name
        location (str): Location of the control
        parent (str): Parent of the control. If empty, the control is
            created at the scene root.
        shape (str): Shape of the control to apply (should be accessible via
            aniseed_toolkit/_resources/shapes). If empty no shape is applied.
        config: The rig configuration instance (required, despite the
            default of None)
        match_to: Optional object to match transform to. If not given,
            the nodes keep the world transform they were created with (the origin).
        shape_scale: Scale of the shape to apply to the control, default is 1.0
        rotate_shape: Optional x, y, z rotation to apply to the shape,
            default is None
        classification_override: By default this will always use the control
            prefix as per the rig configuration, but you can specify an override.
        counter: The counter to use when generating the names, default is 1

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
        counter=counter,
    )


@tool(
    "Get Control",
    classification="Rigging",
    user_facing=False,
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


@tool(
    "Set As Zero Transform",
    classification="Rigging",
)
def set_as_zero_transform(node: str) -> None:
    """
    Makes the current world transform of the control the rest transform of
    its hierarchy: the org, zero, offset and ctl are all moved to the
    current world matrix of the ctl, leaving the ctl with zero values.

    Args:
        node: Any part of a control hierarchy
    """
    # -- Get the node as a control object
    control = Control.get(node)

    # -- Read the world transform
    world_xform = _resolve(control.ctl).get_matrix(space="world")

    # -- We need to reset all of these in this specific order
    items = [
        control.org,
        control.zero,
        control.off,
        control.ctl,
    ]

    for item in items:
        _resolve(item).set_matrix(world_xform, space="world")


def add_offset_control(
        parent_control: "Control",
        description: str,
        location: str,
        config: "aniseed.RigConfiguration",
        shape: str,
        match_to: str,
        rotate_shape=None,
) -> "Control":
    """
    Creates an offset control as a child of the given control, letting
    animators layer offsets on top of the main control. A non-keyable
    ``show_offset`` attribute is also added to the main control.

    Note: the ``show_offset`` attribute is not currently connected to
    anything.

    Args:
        parent_control: The control to add the offset control beneath
        description: The description of the main control. "_offset" is
            appended for the offset control
        location: The location for the offset control
        config: The rig configuration instance
        shape: The shape to apply to the offset control
        match_to: The node to match the offset control's transform to
        rotate_shape: Optional x, y, z rotation to apply to the shape

    Returns:
        The offset control
    """
    show_offset = mref.get(parent_control.ctl).add_attribute(
        "show_offset",
        value=False,
        attribute_type="bool",
        keyable=False,
    )
    show_offset.set(channelBox=True)

    return create(
        description=description + "_offset",
        location=location,
        config=config,
        shape=shape,
        parent=parent_control.ctl,
        match_to=match_to,
        rotate_shape=rotate_shape,
    )


def create_with_offset(
        description: str,
        location: str,
        config: "aniseed.RigConfiguration",
        shape: str,
        parent: str,
        match_to: str,
        align_to_world: bool = False,
        add_offset: bool = False,
        offset_visibility_toggle: bool = False,
) -> typing.Tuple["Control", typing.Optional["Control"]]:
    """
    Creates a control and, optionally, an offset control beneath it, both
    matched to the same node.

    Args:
        description: Descriptive part of the control names. "_offset" is
            appended for the offset control
        location: The location of the controls
        config: The rig configuration instance
        shape: The shape to apply to both controls
        parent: The node the control's org is parented under
        match_to: The node to match both controls' transforms to
        align_to_world: If True, the control's org is given a world rotation
            of [0, 0, 0] before the offset control is created
        add_offset: If True, an offset control is created under the control
        offset_visibility_toggle: If True (and an offset control is created),
            a non-keyable "show_offset" attribute on the control drives the
            visibility of the offset control's shapes

    Returns:
        A tuple of the control and the offset control (None when add_offset
        is False)
    """
    control = create(
        description=description,
        location=location,
        config=config,
        shape=shape,
        parent=parent,
        match_to=match_to,
    )

    if align_to_world:
        mref.get(control.org).set_rotation([0, 0, 0], space="world")

    if not add_offset:
        return control, None

    if offset_visibility_toggle:
        show_offset = mref.get(control.ctl).add_attribute(
            "show_offset",
            value=False,
            attribute_type="bool",
            keyable=False,
        )
        show_offset.set(channelBox=True)

    offset_control = create(
        description=description + "_offset",
        location=location,
        config=config,
        shape=shape,
        parent=control.ctl,
        match_to=match_to,
    )

    if offset_visibility_toggle:
        for shape_node in mref.get(offset_control.ctl).shapes():
            show_offset.connect(shape_node.attr("visibility"))

    return control, offset_control


def has_curve_shapes(node) -> bool:
    """
    Returns True if the given node has at least one nurbsCurve shape.

    Args:
        node: The node (name or mref item) to test
    """
    return bool(mref.get(node).children(node_type="nurbsCurve"))


def curve_controls() -> list[str]:
    """
    Returns every controller tagged node in the scene which has at least one
    nurbsCurve shape.

    The names are returned exactly as maya reports them because callers
    compare and parse them as strings (e.g. for location tokens or skip lists).
    """
    # -- cmds rather than mref, as mref would turn maya's (possibly partial
    # -- path) names into short names
    return [
        node
        for node in cmds.controller(allControllers=True, query=True) or []
        if has_curve_shapes(node)
    ]
