from . import core


# --------------------------------------------------------------------------------------
def rotation_from_up_axis(up_axis):
    """
    Shapes are authored in a Y up environment. If you want to get a rotation vector
    to rotate the shape around based on another axis being up, you can use this
    function to get that vector
    """

    if up_axis == "X":
        return [0, 0, -90]

    if up_axis == "Z":
        return [-90, 0, 0]

    return [0, 0, 0]


# --------------------------------------------------------------------------------------
def align_to_forward_axis(node, forward_axis):
    core.rotate_shape(
        node,
        rotation_from_up_axis(forward_axis)
    )
