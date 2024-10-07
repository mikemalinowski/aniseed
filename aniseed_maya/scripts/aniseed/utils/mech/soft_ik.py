"""
import maya.cmds as mc

from aniseedx.vendor import blackout
blackout.drop("aniseedx")

import aniseedx

aniseedx.utils.elements.soft_ik.create(
    "RootPoint",
    "TipPoint",
    mc.getAttr("joint2.translateX"),
    mc.getAttr("joint3.translateX"),
    "joint2",
    "joint3",
)
"""
import bony
import maya.cmds as mc

from .. import attribute


def create(root, target, second_joint, third_joint, host=None):

    facing_direction = bony.direction.get_chain_facing_direction(
        second_joint,
        third_joint,
    )
    print("Facing Direction: ", facing_direction)
    if not host:
        host = mc.createNode("network")

    float_attrs = {
        "UpperAddition": 0,
        "LowerAddition": 0,
        "DefaultUpperLength": abs(mc.getAttr(f"{second_joint}.tx")),
        "DefaultLowerLength": abs(mc.getAttr(f"{third_joint}.tx")),
        "Stretch": 1,
        "SoftDistance": 0,
    }

    matrix_attrs = {
        "RootMatrix": None,
        "TargetMatrix": None,
    }

    attribute.add_separator_attr(host)

    for attr, value in float_attrs.items():
        mc.addAttr(
            host,
            shortName=attr,
            at="float",
            k=False if "Default" in attr else True,
            dv=value
        )

    default_upper_len_attr = f"{host}.DefaultUpperLength"
    default_lower_len_attr = f"{host}.DefaultLowerLength"
    upper_addition_attr = f"{host}.UpperAddition"
    lower_addition_attr = f"{host}.LowerAddition"
    soft_dist_attr = f"{host}.SoftDistance"
    stretch_attr = f"{host}.Stretch"

    mc.addAttr(
        host,
        shortName="root_matrix",
        at="matrix",
    )
    root_matrix = f"{host}.root_matrix"

    mc.addAttr(
        host,
        shortName="target_matrix",
        at="matrix",
    )
    target_matrix = f"{host}.target_matrix"

    mc.connectAttr(
        f"{root}.worldMatrix[0]",
        root_matrix,
    )

    mc.connectAttr(
        f"{target}.worldMatrix[0]",
        target_matrix,
    )

    max_len_attr = add(
        default_upper_len_attr,
        default_lower_len_attr,
    )

    upper_factor_attr = divide(
        default_upper_len_attr,
        max_len_attr
    )

    lower_factor_attr = divide(
        default_lower_len_attr,
        max_len_attr,
    )

    root_translate_attr = matrix_to_translate(root_matrix)
    target_translate_attr = matrix_to_translate(target_matrix)

    actual_distance_attr = length(
        root_translate_attr,
        target_translate_attr,
    )

    # -- DaU
    overstretch_amount_attr = subtract(
        max_len_attr,
        soft_dist_attr,
    )

    # -- CONDITION
    cond = mc.createNode("condition")

    mc.setAttr(
        f"{cond}.operation",
        2,  # -- Greater Than
    )

    mc.connectAttr(
        actual_distance_attr,
        f"{cond}.firstTerm",
    )

    mc.connectAttr(
        overstretch_amount_attr,
        f"{cond}.secondTerm",
    )

    # -_ FALSE TRACK
    false_upper_add_attr = add(
        default_upper_len_attr,
        upper_addition_attr
    )

    false_lower_add_attr = add(
        default_lower_len_attr,
        lower_addition_attr,
    )

    mc.connectAttr(
        false_upper_add_attr,
        f"{cond}.colorIfFalseR",
    )

    mc.connectAttr(
        false_lower_add_attr,
        f"{cond}.colorIfFalseG",
    )

    # -- TRUE TRACK
    n = subtract(
        actual_distance_attr,
        overstretch_amount_attr,
    )

    n = divide(
        n,
        soft_dist_attr,
    )

    n = multiply(
        n,
        -1,
    )

    n = exp(n)

    n = subtract(
        1,
        n,
    )

    n = multiply(
        n,
        soft_dist_attr,
    )

    n = add(
        n,
        overstretch_amount_attr,
    )

    scale = divide(
        actual_distance_attr,
        n,
    )

    # -- Add it all together
    upper_attr = multiply(
        default_upper_len_attr,
        scale,
    )

    upper_attr = subtract(
        upper_attr,
        default_upper_len_attr
    )

    upper_attr = multiply(
        upper_attr,
        stretch_attr,
    )

    upper_attr = add(
        upper_attr,
        default_upper_len_attr,
    )

    lower_attr = multiply(
        default_lower_len_attr,
        scale,
    )

    lower_attr = subtract(
        lower_attr,
        default_lower_len_attr,
    )

    lower_attr = multiply(
        lower_attr,
        stretch_attr,
    )

    lower_attr = add(
        lower_attr,
        default_lower_len_attr,
    )

    if facing_direction == bony.direction.Facing.NegativeX:
        upper_attr = multiply(
            upper_attr,
            1, #-1,
        )

        lower_attr = multiply(
            lower_attr,
            1, #-1,
        )

    mc.connectAttr(
        upper_attr,
        f"{cond}.colorIfTrueR",
    )

    mc.connectAttr(
        lower_attr,
        f"{cond}.colorIfTrueG"
    )

    # -- Finally, conect the attributes to the joints
    mc.connectAttr(
        f"{cond}.outColorR",
        f"{second_joint}.translateX",
    )

    mc.connectAttr(
        f"{cond}.outColorG",
        f"{third_joint}.translateX",
    )

    pass

def _float_math(first_term, second_term, operation=0):

    add_node = mc.createNode("floatMath")

    mc.setAttr(
        f"{add_node}.operation",
        operation,
    )

    if isinstance(first_term, str):
        mc.connectAttr(
            first_term,
            f"{add_node}.floatA",
        )

    else:
        mc.setAttr(
            f"{add_node}.floatA",
            first_term
        )

    if isinstance(second_term, str):
        mc.connectAttr(
            second_term,
            f"{add_node}.floatB",
        )

    else:
        mc.setAttr(
            f"{add_node}.floatB",
            second_term
        )

    return f"{add_node}.outFloat"

def add(first_term, second_term):
    return _float_math(
        first_term,
        second_term,
        0,  # -- Add
    )


def multiply(first_term, second_term):
    return _float_math(
        first_term,
        second_term,
        2,  # -- Multiply
    )

def divide(first_term, second_term):
    return _float_math(
        first_term,
        second_term,
        3,  # -- Add
    )


def subtract(first_term, second_term):
    return _float_math(
        first_term,
        second_term,
        1,  # -- Subtract
    )


def exp(first_term):

    n = mc.createNode("floatMath")
    mc.setAttr(
        f"{n}.floatB",
        0,
    )
    mc.expression(s=f"{n}.floatA=exp({first_term})")

    return f"{n}.outFloat"

def matrix_to_translate(matrix_attr):

    decompose_node = mc.createNode("decomposeMatrix")

    mc.connectAttr(
        matrix_attr,
        f"{decompose_node}.inputMatrix",
    )

    return f"{decompose_node}.outputTranslate"

def subtract_vector(first_term, second_term):
    node = mc.createNode("colorMath")

    mc.connectAttr(
        first_term,
        f"{node}.colorA"
    )

    mc.connectAttr(
        second_term,
        f"{node}.colorB",
    )

    mc.setAttr(
        f"{node}.operation",
        1,
    )
    return f"{node}.outColor"

def length(first_term, second_term):

    delta_attr = subtract_vector(first_term, second_term)

    len_node = mc.createNode("length")

    mc.connectAttr(
        delta_attr,
        f"{len_node}.input"
    )

    return f"{len_node}.output"

