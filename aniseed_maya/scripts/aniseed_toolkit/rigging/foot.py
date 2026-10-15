"""
Foot pivot and foot roll behaviour shared by the leg components.
"""
import mref

from ..core import attributes as _attributes
from ..rig import control as _control
from ..scene import shapes as _shapes
from ..scene import transforms as _transforms


# -- The tags of the foot pivot guides, in the order the pivots are chained
PIVOT_TAGS = [
    "Ball",
    "Heel",
    "Toe",
    "Inner",
    "Outer",
]


# -- Default local transforms for the pivot guides when they are first created
DEFAULT_GUIDE_TRANSFORMS = {
    "Ball": {},
    "Heel": {"tz": -2, "rz": 90},
    "Toe": {"tz": 2, "rx": 180, "rz": 90},
    "Inner": {"tx": -2, "rx": 90, "rz": 90},
    "Outer": {"tx": 2, "rx": -90, "rz": 90},
}


# -- The axis choices for the foot roll options, mapped to the rotate
# -- attribute and direction they represent
ROLL_AXES = {
    "Positive X": ("rotateX", 1),
    "Negative X": ("rotateX", -1),
    "Positive Y": ("rotateY", 1),
    "Negative Y": ("rotateY", -1),
    "Positive Z": ("rotateZ", 1),
    "Negative Z": ("rotateZ", -1),
}


# -- The names of the component options which take a ROLL_AXES key
ROLL_AXIS_OPTIONS = [
    "Roll Heel Control Axis",
    "Roll Toe Pivot Axis",
    "Roll Heel Pivot Axis",
]


# -- The largest roll (in degrees) the foot roll network will pass through
MAX_ROLL = 360.0


def create_guides(description_prefix: str, location: str, config) -> dict[str, str]:
    """
    Creates a guide for each foot pivot, with its default transform.

    Args:
        description_prefix: Prefix for the guide descriptions
        location: The location to use when naming
        config: The rig configuration

    Returns:
        A dictionary of pivot tag to guide
    """
    guides = dict()

    for tag in PIVOT_TAGS:
        guide = mref.create(
            "transform",
            name=config.generate_name(
                classification="gde",
                description=f"{description_prefix}{tag}",
                location=location,
            ),
        )
        _shapes.load_shape(guide.name(), "core_rotator")

        for attribute, value in DEFAULT_GUIDE_TRANSFORMS[tag].items():
            guide.attr(attribute).set(value)

        guides[tag] = guide.name()

    return guides


def create_pivots(
        foot_control,
        guides: dict[str, str],
        prefix: str,
        location: str,
        config,
        prefix_separator: str = "",
        prefix_pivot_transforms: bool = False,
        add_separator: bool = False,
        match_controls_on_creation: bool = False,
) -> tuple[str, list[str], dict[str, str]]:
    """
    Creates a chain of pivot controls under the foot control - one for
    each pivot tag - each with a pivot transform beneath it which rotates
    from a "<tag>_roll" attribute on the foot control.

    Args:
        foot_control: The foot control (Control) to build the pivots under
        guides: Dictionary of pivot tag to the guide to place it at
        prefix: The descriptive prefix to name the pivot controls with
        location: The location to use when naming
        config: The rig configuration
        prefix_separator: Text placed between the prefix and the pivot
            description (only when there is a prefix)
        prefix_pivot_transforms: If True the pivot transforms are given the
            same prefixed description as the controls
        add_separator: If True a separator attribute is added to the foot
            control before the roll attributes
        match_controls_on_creation: If True the pivot controls are matched
            to the guides as they are created, otherwise the org of the
            control is placed at the guide afterwards

    Returns:
        The last pivot transform (which is the parent for anything which
        should be affected by the pivots), the list of pivot controls and
        a dictionary of pivot tag to pivot transform.
    """
    if add_separator:
        _attributes.add_separator(foot_control.ctl)

    if prefix:
        prefix = prefix + prefix_separator

    foot = mref.get(foot_control.ctl)
    last_parent = foot_control.ctl
    controls = []
    pivots = dict()

    for tag in PIVOT_TAGS:
        description = f"{tag.lower()}_roll"
        guide = guides[tag]

        pivot_control = _control.create(
            description=f"{prefix}{description}",
            location=location,
            parent=last_parent,
            shape="core_sphere",
            shape_scale=4,
            config=config,
            match_to=guide if match_controls_on_creation else None,
        )

        if not match_controls_on_creation:
            mref.get(pivot_control.org).set_matrix(
                mref.get(guide).get_matrix(space="world"),
                space="world",
            )

        pivot = _transforms.create(
            classification="piv",
            description=f"{prefix}{description}" if prefix_pivot_transforms else description,
            location=location,
            config=config,
            parent=pivot_control.ctl,
            match_to=pivot_control.ctl,
        )

        # -- Add the parameter to the foot control which rotates the pivot
        roll_attribute = foot.add_attribute(
            description,
            value=None,
            attribute_type="float",
            defaultValue=0,
            keyable=True,
        )
        roll_attribute.connect(f"{pivot}.rotateY")

        controls.append(pivot_control.ctl)
        pivots[tag] = pivot
        last_parent = pivot

    return last_parent, controls, pivots


def create_roll(
        foot_control,
        heel_control,
        pivots: dict[str, str],
        heel_angle: float,
        heel_control_axis: str,
        toe_pivot_axis: str,
        heel_pivot_axis: str,
):
    """
    Adds a "roll" attribute to the foot control. Positive roll first
    rotates the heel control (lifting the heel) up to the roll_heel_angle,
    after which the remaining roll rotates the toe pivot. Negative roll
    rocks the foot back on the heel pivot.

    The roll_heel_angle attribute is also added to the foot control, with
    the given heel angle as its starting value.

    Args:
        foot_control: The foot control (Control) to add the attributes to
        heel_control: The heel control (Control) which positive roll lifts
        pivots: Dictionary of pivot tag to pivot transform
        heel_angle: The starting value of the roll_heel_angle attribute
        heel_control_axis: ROLL_AXES key for the heel control rotation
        toe_pivot_axis: ROLL_AXES key for the toe pivot rotation
        heel_pivot_axis: ROLL_AXES key for the heel pivot rotation
    """
    heel_control_attribute, heel_control_sign = ROLL_AXES[heel_control_axis]
    toe_pivot_attribute, toe_pivot_sign = ROLL_AXES[toe_pivot_axis]
    heel_pivot_attribute, heel_pivot_sign = ROLL_AXES[heel_pivot_axis]

    foot = mref.get(foot_control.ctl)

    roll = foot.add_attribute(
        "roll",
        value=None,
        attribute_type="float",
        defaultValue=0,
        keyable=True,
    )

    # -- The heel angle is exposed so the animator can adjust it
    heel_angle_attribute = foot.add_attribute(
        "roll_heel_angle",
        value=None,
        attribute_type="float",
        defaultValue=heel_angle,
        minValue=0,
        keyable=True,
    )

    # -- The roll beyond the heel angle is what drives the toe
    roll_past_heel = mref.create("floatMath")
    roll_past_heel.operation.set(1)  # -- Subtract
    roll.connect(roll_past_heel.floatA)
    heel_angle_attribute.connect(roll_past_heel.floatB)

    # -- Split the roll into its three stages:
    # -- R : 0 to the heel angle, for the heel control
    # -- G : anything beyond the heel angle, for the toe pivot
    # -- B : anything below zero, for the heel pivot
    stages = mref.create("clamp")

    roll.connect(stages.inputR)
    stages.minR.set(0)
    heel_angle_attribute.connect(stages.maxR)

    roll_past_heel.outFloat.connect(stages.inputG)
    stages.minG.set(0)
    stages.maxG.set(MAX_ROLL)

    roll.connect(stages.inputB)
    stages.minB.set(-MAX_ROLL)
    stages.maxB.set(0)

    # -- The negative stage is already negative, so its sign is flipped
    # -- to make "Positive" mean the direction negative roll rocks towards
    _add_rotation_driver(
        f"{heel_control.off}.{heel_control_attribute}",
        _signed(stages.outputR, heel_control_sign),
    )
    _add_rotation_driver(
        f"{pivots['Toe']}.{toe_pivot_attribute}",
        _signed(stages.outputG, toe_pivot_sign),
    )
    _add_rotation_driver(
        f"{pivots['Heel']}.{heel_pivot_attribute}",
        _signed(stages.outputB, -heel_pivot_sign),
    )


def _signed(attribute, sign: int):
    """
    Returns an attribute carrying the given attribute's value multiplied
    by the sign.
    """
    result = mref.create("floatMath")
    result.operation.set(2)  # -- Multiply
    attribute.connect(result.floatA)
    result.floatB.set(sign)
    return result.outFloat


def _add_rotation_driver(target: str, source) -> None:
    """
    Connects the source into the target attribute. If the target is
    already driven, the existing driver and the source are summed.
    """
    target = mref.get(target)
    existing = target.inputs()

    if not existing:
        source.connect(target)
        return

    total = mref.create("floatMath")
    total.operation.set(0)  # -- Add
    existing[0].connect(total.floatA)
    source.connect(total.floatB)
    total.outFloat.connect(target, force=True)
