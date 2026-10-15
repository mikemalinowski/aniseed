"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.core.maths, aniseed_toolkit.rig.pose_mixer, aniseed_toolkit.scene.transforms
"""
import warnings

from ..core.maths import calculate_four_point_spline_positions, calculate_upvector_position, direction_between, distance_between, factor_between, interpolate_vector, timed_function_call
from ..rig.pose_mixer import TransformMixer
from ..scene.transforms import aim_at, apply_relative_matrix, get_relative_matrix, position_between, scale_translation, scale_translation_of_hierarchy, snap_position

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.core.maths, aniseed_toolkit.rig.pose_mixer, aniseed_toolkit.scene.transforms",
    DeprecationWarning,
    stacklevel=2,
)

_LAZY = {
}


def __getattr__(name):
    # -- Names which moved into aniseed are resolved on first use so
    # -- that the toolkit never imports aniseed when it is loaded
    if name in _LAZY:
        import importlib
        module, attribute = _LAZY[name]
        return getattr(importlib.import_module(module), attribute)
    from .._legacy import resolve
    return resolve(__name__, name)
