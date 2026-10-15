"""
Conversion between centimetres and the scene's linear unit, for values and
matrices.
"""
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


def _factor(table: dict) -> float:
    """
    Returns the factor for the scene's current linear unit from the given
    table, raising a ValueError if the unit is not in it.
    """
    # -- cmds rather than the mref passthrough: mref converts string
    # -- results to nodes, so a node named like a unit ("m", "cm") would be
    # -- returned instead of the unit
    current_unit = cmds.currentUnit(query=True, linear=True)

    if current_unit not in table:
        raise ValueError(
            "Unsupported Maya unit: {}".format(current_unit)
        )

    return table[current_unit]


def _scale_matrix_translation(matrix, table: dict) -> list:
    """
    Returns a copy of the flat 4x4 matrix with its translation scaled by
    the factor for the scene's current linear unit from the given table.
    """
    if len(matrix) != 16:
        raise ValueError("Matrix must contain exactly 16 floats")

    scale = _factor(table)

    result = list(matrix)

    # Maya matrices store translation in indices 12, 13, 14
    result[12] *= scale
    result[13] *= scale
    result[14] *= scale

    return result


def from_cm(value_in_cm: float) -> float:
    """
    Converts a value in centimetres to the scene's current linear unit.

    Args:
        value_in_cm: The value in centimetres

    Returns:
        The value in the scene's linear unit

    Raises:
        ValueError: If the scene's linear unit is not supported
    """
    return value_in_cm * _factor(cm_to_unit)


def to_cm(value):
    """
    Converts a value in the scene's current linear unit to centimetres.

    Example:
        Maya unit = meters
        1.0 -> 100.0 cm

        Maya unit = inches
        1.0 -> 2.54 cm

    Args:
        value: The value in the scene's linear unit

    Returns:
        The value in centimetres

    Raises:
        ValueError: If the scene's linear unit is not supported
    """
    return value * _factor(unit_to_cm)


def matrix_from_cm(matrix):
    """
    Converts a 4x4 matrix whose translation is in centimetres to the
    scene's current linear unit. Only the translation is scaled.

    Args:
        matrix: Flat list/tuple of 16 floats

    Returns:
        A new list of 16 floats

    Raises:
        ValueError: If the matrix does not have 16 values, or the scene's
            linear unit is not supported
    """
    return _scale_matrix_translation(matrix, cm_to_unit)


def matrix_to_cm(matrix):
    """
    Converts a 4x4 matrix whose translation is in the scene's current
    linear unit to centimetres. Only the translation is scaled.

    Args:
        matrix: Flat list/tuple of 16 floats

    Returns:
        A new list of 16 floats

    Raises:
        ValueError: If the matrix does not have 16 values, or the scene's
            linear unit is not supported
    """
    return _scale_matrix_translation(matrix, unit_to_cm)
