import maya.cmds as mc

from . import hierarchy


# TODO : I need a get index from full direction array (positive x, positive y, positive etc)

# ----------------------------------------------------------------------------------
class Facing:

    PositiveX = 0
    PositiveY = 1
    PositiveZ = 2

    NegativeX = 3
    NegativeY = 4
    NegativeZ = 6

    Unknown = 7


# --------------------------------------------------------------------------------------
def get_chain_facing_direction(start, end, epsilon=0.01):

    axis = dict(
        x=0,
        y=0,
        z=0,
    )

    for joint in hierarchy.get_between(start, end)[1:]:
        for channel in axis:
            axis[channel] += mc.getAttr(
                f"{joint}.translate{channel.upper()}",
            )

    has_x = abs(axis["x"]) > epsilon
    has_y = abs(axis["y"]) > epsilon
    has_z = abs(axis["z"]) > epsilon

    if sum([int(has_x), int(has_y), int(has_z)]) > 1:
        return Facing.Unknown

    if has_x and axis["x"] > 0:
        return Facing.PositiveX

    if has_x and axis["x"] < 0:
        return Facing.NegativeX

    if has_y and axis["y"] > 0:
        return Facing.PositiveY

    if has_y and axis["y"] < 0:
        return Facing.NegativeY

    if has_z and axis["z"] > 0:
        return Facing.PositiveZ

    if has_z and axis["z"] < 0:
        return  Facing.NegativeZ

    return Facing.Unknown


# --------------------------------------------------------------------------------------
def get_axis_from_direction(direction):

    if direction == Facing.NegativeX or direction == Facing.PositiveX:
        return "X"

    if direction == Facing.NegativeY or direction == Facing.PositiveY:
        return "Y"

    if direction == Facing.NegativeZ or direction == Facing.PositiveZ:
        return "Z"

# --------------------------------------------------------------------------------------
def get_multiplier_from_direction(direction):

    if direction == Facing.NegativeX or direction == Facing.NegativeY or direction == Facing.NegativeZ:
        return -1

    return 1


# --------------------------------------------------------------------------------------
def get_ik_solver_attribute_index(direction):

    if direction == Facing.PositiveX:
        return 0

    elif direction == Facing.NegativeX:
        return 1

    elif direction == Facing.PositiveY:
        return 2

    elif direction == Facing.NegativeY:
        return 3

    elif direction == Facing.PositiveZ:
        return 4

    return 5


# --------------------------------------------------------------------------------------
def get_direction_from_axis(axis):

    if axis.lower() == "x":
        return Facing.PositiveX

    if axis.lower() == "y":
        return Facing.PositiveY

    if axis.lower() == "z":
        return Facing.PositiveZ

    return Facing.Unknown


# --------------------------------------------------------------------------------------
def get_cross_axis(axis):

    if axis.lower() == "x":
        return "Y"

    if axis.lower() == "y":
        return "Z"

    return "X"


# --------------------------------------------------------------------------------------
def axis_vector(axis):

    if axis.lower() == "x":
        return [1, 0, 0]

    elif axis.lower() == "y":
        return [0, 1, 0]

    else:
        return [0, 0, 1]

