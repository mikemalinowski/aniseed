import mref
import aniseed_toolkit

from .node_math import add, subtract, multiply, divide, exp, matrix_to_translate, length


def create_two_bone_soft_ik(root, target, second_joint, third_joint, host=None):
    """
    Applies soft ik to a two bone chain by driving the translateX of the
    second and third joints.

    Args:
        root: A node representing the root of the chain
        target: A node representing the ik target
        second_joint: The second joint of the chain
        third_joint: The third (end) joint of the chain
        host: The node to add the soft ik attributes to. A network node
            is created if this is not given.
    """
    facing_direction = aniseed_toolkit.direction.get_chain_facing_direction(
        second_joint,
        third_joint,
    )

    if not host:
        host = mref.create("network").name()

    float_attrs = {
        "UpperAddition": 0,
        "LowerAddition": 0,
        "DefaultUpperLength": abs(mref.get(f"{second_joint}.tx").get()),
        "DefaultLowerLength": abs(mref.get(f"{third_joint}.tx").get()),
        "Stretch": 1,
        "SoftDistance": 0,
    }

    aniseed_toolkit.attributes.add_separator(host)

    host_node = mref.get(host)
    for attr, value in float_attrs.items():
        host_node.add_attribute(
            attr,
            value=None,
            attribute_type="float",
            keyable="Default" not in attr,
            defaultValue=value,
        )

    default_upper_len_attr = f"{host}.DefaultUpperLength"
    default_lower_len_attr = f"{host}.DefaultLowerLength"
    upper_addition_attr = f"{host}.UpperAddition"
    lower_addition_attr = f"{host}.LowerAddition"
    soft_dist_attr = f"{host}.SoftDistance"
    stretch_attr = f"{host}.Stretch"

    root_matrix = _add_matrix_attribute(host, "root_matrix")
    target_matrix = _add_matrix_attribute(host, "target_matrix")

    mref.get(root).attr("worldMatrix[0]").connect(root_matrix)
    mref.get(target).attr("worldMatrix[0]").connect(target_matrix)

    max_len_attr = add(
        add(add(default_upper_len_attr, upper_addition_attr), lower_addition_attr),
        default_lower_len_attr,
    )

    # -- These length factors are not used by the network, but the nodes
    # -- are kept so that the names of every node created after them are
    # -- unchanged.
    divide(default_upper_len_attr, max_len_attr)
    divide(default_lower_len_attr, max_len_attr)

    actual_distance_attr = length(
        matrix_to_translate(root_matrix),
        matrix_to_translate(target_matrix),
    )

    overstretch_amount_attr = subtract(max_len_attr, soft_dist_attr)

    # -- When the distance is greater than the overstretch amount we take
    # -- the true (soft) track, otherwise the false (rigid) track
    condition = mref.create("condition")
    condition.operation.set(2)  # -- Greater Than
    mref.get(actual_distance_attr).connect(condition.firstTerm)
    mref.get(overstretch_amount_attr).connect(condition.secondTerm)

    # -- FALSE TRACK
    mref.get(add(default_upper_len_attr, upper_addition_attr)).connect(condition.colorIfFalseR)
    mref.get(add(default_lower_len_attr, lower_addition_attr)).connect(condition.colorIfFalseG)

    # -- TRUE TRACK
    scale = _soft_scale(actual_distance_attr, overstretch_amount_attr, soft_dist_attr)

    upper_attr = _stretched_length(default_upper_len_attr, upper_addition_attr, scale, stretch_attr)
    lower_attr = _stretched_length(default_lower_len_attr, lower_addition_attr, scale, stretch_attr)

    if facing_direction == facing_direction.NegativeX:
        # -- These multipliers are deliberately 1 (the -1 was disabled),
        # -- the nodes are kept to retain the node naming
        upper_attr = multiply(upper_attr, 1)
        lower_attr = multiply(lower_attr, 1)

    mref.get(upper_attr).connect(condition.colorIfTrueR)
    mref.get(lower_attr).connect(condition.colorIfTrueG)

    # -- Finally, connect the attributes to the joints
    condition.outColorR.connect(f"{second_joint}.translateX")
    condition.outColorG.connect(f"{third_joint}.translateX")


def _add_matrix_attribute(host: str, name: str) -> str:
    """
    Adds a matrix attribute (if it does not already exist) and returns
    its address
    """
    address = f"{host}.{name}"
    if not mref.objExists(address):
        mref.addAttr(host, shortName=name, attributeType="matrix")
    return address


def _soft_scale(actual_distance_attr: str, overstretch_amount_attr: str, soft_dist_attr: str) -> str:
    """
    Builds the soft ik falloff, returning the scale factor to apply
    to the bone lengths
    """
    n = subtract(actual_distance_attr, overstretch_amount_attr)
    n = divide(n, soft_dist_attr)
    n = multiply(n, -1)
    n = exp(n)
    n = subtract(1, n)
    n = multiply(n, soft_dist_attr)
    n = add(n, overstretch_amount_attr)
    return divide(actual_distance_attr, n)


def _stretched_length(default_length_attr, addition_attr, scale: str, stretch_attr: str) -> str:
    """
    Returns the length of a bone when scaled by the soft ik, blended by
    the stretch attribute and including the user addition
    """
    result = multiply(default_length_attr, scale)
    result = subtract(result, default_length_attr)
    result = multiply(result, stretch_attr)
    result = add(result, default_length_attr)
    return add(result, addition_attr)
