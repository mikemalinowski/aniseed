from maya import cmds

# Conversion factors from cm
cm_to_unit = {
    "mm": 10.0,
    "cm": 1.0,
    "m": 0.01,
    "km": 0.00001,

    "in": 0.3937007874,
    "ft": 0.032808399,
    "yd": 0.010936133,
    "mi": 0.0000062137,
}

# Conversion factors to centimeters
unit_to_cm = {
    "mm": 0.1,
    "cm": 1.0,
    "m": 100.0,
    "km": 100000.0,

    "in": 2.54,
    "ft": 30.48,
    "yd": 91.44,
    "mi": 160934.4,
}

def from_cm(value_in_cm: float) -> float:
    """
    This takes in a value based on 1 unit = 1cm and will rescale that
    value based on maya's current setup.
    """

    current_unit = cmds.currentUnit(query=True, linear=True)

    if current_unit not in cm_to_unit:
        raise ValueError(
            "Unsupported Maya unit: {}".format(current_unit)
        )

    return value_in_cm * cm_to_unit[current_unit]


def to_cm(value):
    """
    Convert a value from Maya's current linear working unit
    into centimeters.

    Example:
        Maya unit = meters
        1.0 -> 100.0 cm

        Maya unit = inches
        1.0 -> 2.54 cm
    """
    current_unit = cmds.currentUnit(query=True, linear=True)

    if current_unit not in unit_to_cm:
        raise ValueError(
            "Unsupported Maya unit: {}".format(current_unit)
        )

    return value * unit_to_cm[current_unit]




def matrix_from_cm(matrix):
    """
    Convert a 4x4 matrix whose translation is assumed to be in centimeters
    into Maya's current working linear unit.

    Input:
        flat list/tuple of 16 floats

    Returns:
        new list of 16 floats
    """

    if len(matrix) != 16:
        raise ValueError("Matrix must contain exactly 16 floats")

    current_unit = cmds.currentUnit(query=True, linear=True)

    if current_unit not in cm_to_unit:
        raise ValueError(
            "Unsupported Maya unit: {}".format(current_unit)
        )

    scale = cm_to_unit[current_unit]

    result = list(matrix)

    # Maya matrices store translation in indices 12, 13, 14
    result[12] *= scale
    result[13] *= scale
    result[14] *= scale

    return result



def matrix_to_cm(matrix):
    """
    Convert a 4x4 matrix whose translation is in Maya's current
    working linear unit into centimeters.

    Input:
        flat list/tuple of 16 floats

    Returns:
        new list of 16 floats
    """

    if len(matrix) != 16:
        raise ValueError("Matrix must contain exactly 16 floats")

    current_unit = cmds.currentUnit(query=True, linear=True)

    if current_unit not in unit_to_cm:
        raise ValueError(
            "Unsupported Maya unit: {}".format(current_unit)
        )

    scale = unit_to_cm[current_unit]

    result = list(matrix)

    # Maya matrices store translation in indices 12, 13, 14
    result[12] *= scale
    result[13] *= scale
    result[14] *= scale

    return result
