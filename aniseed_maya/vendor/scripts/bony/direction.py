import maya.cmds as mc

from . import hierarchy


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
def direction_as_string(direction):
    if direction == Facing.PositiveX: return "Positive X"
    if direction == Facing.NegativeX: return "Negative X"
    if direction == Facing.PositiveY: return "Positive Y"
    if direction == Facing.NegativeY: return "Negative Y"
    if direction == Facing.PositiveZ: return "Positive Z"
    if direction == Facing.NegativeZ: return "Negative Z"

    return "Unknown"


# --------------------------------------------------------------------------------------
def direction_from_string(direction_string):
    direction_string = direction_string.lower()

    if direction_string[-1] == "x":
        if "negative" in direction_string:
            return Facing.NegativeX
        return Facing.PositiveX

    if direction_string[-1] == "y":
        if "negative" in direction_string:
            return Facing.NegativeY
        return Facing.PositiveY

    if direction_string[-1] == "z":
        if "negative" in direction_string:
            return Facing.NegativeZ
        return Facing.PositiveZ


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
def get_chain_facing_axis(start, end, epsilon=0.01):
        return get_axis_from_direction(
            get_chain_facing_direction(
                start,
                end,
            )
        )

# --------------------------------------------------------------------------------------
def get_axis_from_direction(direction):

    if direction == Facing.NegativeX or direction == Facing.PositiveX:
        return "X"

    if direction == Facing.NegativeY or direction == Facing.PositiveY:
        return "Y"

    if direction == Facing.NegativeZ or direction == Facing.PositiveZ:
        return "Z"


# --------------------------------------------------------------------------------------
def get_upvector_direction(start, end, epsilon=0.01):

    all_joints = hierarchy.get_between(start, end)

    temp_a = mc.createNode("transform")
    temp_b = mc.createNode("transform")

    facing_direction = get_chain_facing_direction(start, end, epsilon)

    mc.parent(temp_b, temp_a)

    mc.xform(
        temp_a,
        matrix=mc.xform(
            all_joints[0],
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    mc.xform(
        temp_b,
        matrix=mc.xform(
            all_joints[1],
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    highest_rotation_value = 0
    recorded_value = 0
    rotate_axis = "X"

    for idx, axis in enumerate(["X", "Y", "Z"]):
        value = mc.getAttr(f"{temp_b}.rotate{axis}")
        if abs(value) > highest_rotation_value:
            rotate_axis = axis
            highest_rotation_value = abs(value)
            recorded_value = value

    mc.delete(temp_a)

    if facing_direction == Facing.PositiveX and rotate_axis == "Z":
        if recorded_value >= 0:
            return Facing.NegativeY
        return Facing.PositiveY

    if facing_direction == Facing.NegativeX and rotate_axis == "Z":
        if recorded_value >= 0:
            return Facing.PositiveY
        return Facing.NegativeY

    if facing_direction == Facing.PositiveX and rotate_axis == "Y":
        if recorded_value >= 0:
            return Facing.PositiveZ
        return Facing.NegativeZ

    if facing_direction == Facing.NegativeX and rotate_axis == "Y":
        if recorded_value >= 0:
            return Facing.NegativeZ
        return Facing.PositiveZ


    if facing_direction == Facing.PositiveY and rotate_axis == "Z":
        if recorded_value >= 0:
            return Facing.PositiveX
        return Facing.NegativeX

    if facing_direction == Facing.NegativeY and rotate_axis == "Z":
        if recorded_value >= 0:
            return Facing.NegativeX
        return Facing.PositiveX

    if facing_direction == Facing.PositiveY and rotate_axis == "X":
        if recorded_value >= 0:
            return Facing.NegativeZ
        return Facing.PositiveZ

    if facing_direction == Facing.NegativeY and rotate_axis == "X":
        if recorded_value >= 0:
            return Facing.PositiveZ
        return Facing.NegativeZ


    if facing_direction == Facing.PositiveZ and rotate_axis == "Y":
        if recorded_value >= 0:
            return Facing.NegativeX
        return Facing.PositiveX

    if facing_direction == Facing.NegativeZ and rotate_axis == "Y":
        if recorded_value >= 0:
            return Facing.PositiveX
        return Facing.NegativeX


    if facing_direction == Facing.PositiveZ and rotate_axis == "X":
        if recorded_value >= 0:
            return Facing.PositiveY
        return Facing.NegativeY

    if facing_direction == Facing.NegativeZ and rotate_axis == "X":
        if recorded_value >= 0:
            return Facing.NegativeY
        return Facing.PositiveY

    return Facing.Unknown


# --------------------------------------------------------------------------------------
def get_upvector_axis(start, end, epsilon=0.01):
    return get_axis_from_direction(
        get_upvector_direction(start, end, epsilon)
    )

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


# --------------------------------------------------------------------------------------
def direction_vector(direction):
    if direction == Facing.PositiveX: return [1, 0, 0]
    if direction == Facing.NegativeX: return [-1, 0, 0]

    if direction == Facing.PositiveY: return [0, 1, 0]
    if direction == Facing.NegativeY: return [0, -1, 0]

    if direction == Facing.PositiveZ: return [0, 0, 1]
    if direction == Facing.NegativeZ: return [0, 0, -1]