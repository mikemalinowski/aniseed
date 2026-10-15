"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.rig.controls, aniseed_toolkit.scene.shapes
"""
import warnings

from ..rig.controls import mirror_control_shapes as global_mirror
from ..scene.shapes import apply_color, combine, load_shape, mirror, mirror_across, offset, rotate, save_to_file, scale, select_shapes, shape_data_from_file, shape_to_dict

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.rig.controls, aniseed_toolkit.scene.shapes",
    DeprecationWarning,
    stacklevel=2,
)
