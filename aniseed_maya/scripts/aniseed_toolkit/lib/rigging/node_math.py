"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.node_math
"""
import warnings

from ...scene.node_math import ADD, DIVIDE, MULTIPLY, SUBTRACT, add, divide, exp, length, matrix_to_translate, multiply, subtract, subtract_vector

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.node_math",
    DeprecationWarning,
    stacklevel=2,
)
