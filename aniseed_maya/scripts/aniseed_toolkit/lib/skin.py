"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.skin
"""
import warnings

from ..scene.skin import LocalisedSkinCopy, SkinLerper, add_all_skin_joints_to_all_skins, add_all_skin_joints_to_target_meshes, copy_skin_to_unbound_meshes, copy_weight_values_to_destination, declare_weight_value_copy_destination, dict_to_skin, disconnect_all_skins, load, reconnect_all_skins, save, skin_to_dict

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.skin",
    DeprecationWarning,
    stacklevel=2,
)
