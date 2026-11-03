"""
Blend rotators: a control whose offset is parent constrained between two
targets, with a keyable Blend attribute on the control weighting them, which
then drives a joint. Typically used for helper joints at a knuckle or elbow
which should take a share of the rotation between two bones.
"""
import typing

import mref

from . import control as _control
from ..scene import constraints as _constraints

if typing.TYPE_CHECKING:
    import aniseed


def create(
        joint: str,
        target_a: str,
        target_b: str,
        description: str,
        location: str,
        config: "aniseed.RigConfiguration",
        parent: str = None,
        blend: float = 0.5,
        shape: str = "core_cube",
        shape_scale: float = 1.0,
) -> _control.Control:
    """
    Creates a control matched to the joint with a keyable Blend attribute,
    parent constrains the control's offset to both targets (no flip
    interpolation) with Blend weighting them, and parent and scale constrains
    the joint to the control.

    Args:
        joint: The joint the blend rotator drives
        target_a: The target followed when Blend is 0
        target_b: The target followed when Blend is 1
        description: The description for the control's name
        location: The location for the control's name
        config: The rig configuration
        parent: Optional parent for the control
        blend: The starting value of the Blend attribute
        shape: The control shape
        shape_scale: The scale of the control shape

    Returns:
        The created control
    """
    rotator_control = _control.create(
        description=description,
        location=location,
        parent=parent,
        config=config,
        shape=shape,
        match_to=joint,
        shape_scale=shape_scale,
    )

    blend_attribute = mref.get(rotator_control.ctl).add_attribute(
        "Blend",
        value=blend,
        attribute_type="float",
        keyable=True,
    )

    # -- Constrain the control's offset to both targets, with the blend
    # -- attribute driving the weighting between them
    mref.parentConstraint(
        target_a,
        rotator_control.off,
        maintainOffset=True,
    )

    constraint = mref.parentConstraint(
        target_b,
        rotator_control.off,
        maintainOffset=True,
    )[0]
    constraint.attr("interpType").set(0)  # -- No Flip

    reverse = _constraints.blend_weights(blend_attribute, constraint)
    reverse.rename(config.generate_name(
        classification=config.mechanical,
        description=f"{description}Reverse",
        location=location,
    ))

    # -- The control then drives the joint
    _constraints.parent_and_scale(
        rotator_control.ctl,
        joint,
        maintain_offset=True,
    )

    return rotator_control
