"""
Deprecated location, kept for compatibility until aniseed_toolkit 4.0.

Everything here now lives in: aniseed_toolkit.scene.joints
"""
import warnings

from ..scene.joints import HeldTransforms, chain_from_ordered_dict, chain_length, copy_attributes, create, create_spread, create_twist_joints, get_between, is_referenced, make_referenced, move_orients_to_rotation, move_rotations_to_orients, reparent_unknown_children, replicate, replicate_chain, replicate_entire_chain, reverse_chain, roll, unreference

warnings.warn(
    f"{__name__} is deprecated, use aniseed_toolkit.scene.joints",
    DeprecationWarning,
    stacklevel=2,
)
