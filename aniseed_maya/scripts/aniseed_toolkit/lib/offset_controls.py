"""
Helpers for layering offset controls on top of standard controls.
"""
import mref

from . import control as _control


def add_offset_control(
        parent_control: "_control.Control",
        description: str,
        location: str,
        config: "aniseed.RigConfiguration",
        shape: str,
        match_to: str,
        rotate_shape=None,
) -> "_control.Control":
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

    return _control.create(
        description=description + "_offset",
        location=location,
        config=config,
        shape=shape,
        parent=parent_control.ctl,
        match_to=match_to,
        rotate_shape=rotate_shape,
    )
