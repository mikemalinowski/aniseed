"""
This is an implementation of Soft IK which works for n-bone
chains and does not require a custom node implementation.
"""
import mref
import aniseed_toolkit

from .node_math import add, multiply, subtract, matrix_to_translate, length
from .softik import _add_matrix_attribute, _soft_scale


def create_multi_bone_soft_ik(root_target, end_target, root_joint, end_joint, host=None):
    """
    This will create a Soft IK setup to a pre-existing n-bone IK setup.

    Args:
        root_target: A node to represent the roots transform
        end_target: A node which we can track for distances (typically whatever
            is driving the pre-existing ik handle
        root_joint: The first joint in the chain
        end_joint: The last joint in the chain
        host: The node which all the attributes should be added to

    Returns:
        None
    """
    facing_direction = aniseed_toolkit.direction.get_chain_facing_direction(
        root_joint,
        end_joint,
    )

    full_chain = aniseed_toolkit.joints.get_between(
        root_joint,
        end_joint,
    )

    if not host:
        host = mref.create("network").name()

    float_attrs = {
        "Stretch": 1,
        "SoftDistance": 0,
    }

    # -- Note that the default lengths are baked into the network as values
    # -- rather than being read from these attributes
    default_lengths = []
    for idx, joint in enumerate(full_chain[1:]):
        default_length = abs(mref.get(f"{joint}.tx").get())
        float_attrs[f"Joint{idx}Addition"] = 0
        float_attrs[f"Joint{idx}DefaultLength"] = default_length
        default_lengths.append(default_length)

    aniseed_toolkit.attributes.add_separator(host)

    host_node = mref.get(host)
    for attr, value in float_attrs.items():
        if not host_node.has_attribute(attr):
            host_node.add_attribute(
                attr,
                value=None,
                attribute_type="float",
                keyable="Default" not in attr,
                defaultValue=value,
            )

    addition_attrs = [f"{host}.Joint{idx}Addition" for idx in range(len(default_lengths))]
    soft_dist_attr = f"{host}.SoftDistance"
    stretch_attr = f"{host}.Stretch"

    root_matrix = _add_matrix_attribute(host, "root_matrix")
    target_matrix = _add_matrix_attribute(host, "target_matrix")

    mref.get(root_target).attr("worldMatrix[0]").connect(root_matrix)
    mref.get(end_target).attr("worldMatrix[0]").connect(target_matrix)

    max_len_attr = 0
    for default_length, addition_attr in zip(default_lengths, addition_attrs):
        max_len_attr = add(add(default_length, addition_attr), max_len_attr)

    actual_distance_attr = length(
        matrix_to_translate(root_matrix),
        matrix_to_translate(target_matrix),
    )

    overstretch_amount_attr = subtract(max_len_attr, soft_dist_attr)

    # -- One condition per bone. When the distance is greater than the
    # -- overstretch amount we take the true (soft) track, otherwise the
    # -- false (rigid) track
    conditions = []
    for default_length, addition_attr in zip(default_lengths, addition_attrs):
        condition = mref.create("condition")
        condition.operation.set(2)  # -- Greater Than
        mref.get(actual_distance_attr).connect(condition.firstTerm)
        mref.get(overstretch_amount_attr).connect(condition.secondTerm)

        mref.get(add(default_length, addition_attr)).connect(condition.colorIfFalseR)
        conditions.append(condition)

    # -- TRUE TRACK
    scale = _soft_scale(actual_distance_attr, overstretch_amount_attr, soft_dist_attr)

    multiplier = -1 if facing_direction == facing_direction.NegativeX else 1

    for idx, (default_length, addition_attr) in enumerate(zip(default_lengths, addition_attrs)):
        bone_length = multiply(default_length, scale)
        bone_length = subtract(bone_length, default_length)
        bone_length = multiply(bone_length, stretch_attr)
        bone_length = add(bone_length, default_length)
        bone_length = add(bone_length, addition_attr)

        mref.get(bone_length).connect(conditions[idx].colorIfTrueR)

        # -- Finally, connect the attributes to the joints
        mref.get(multiply(conditions[idx].outColorR.full_name(), multiplier)).connect(
            f"{full_chain[idx + 1]}.translateX",
            force=True,
        )
