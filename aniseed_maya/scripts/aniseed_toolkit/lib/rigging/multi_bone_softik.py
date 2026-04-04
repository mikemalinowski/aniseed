"""
This is an implementation of Soft IK which works for n-bone
chains and does not require a custom node implementation.
"""
import aniseed_toolkit
import maya.cmds as mc


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
    facing_direction = aniseed_toolkit.run(
        "Get Chain Facing Direction",
        root_joint,
        end_joint,
    )

    full_chain = aniseed_toolkit.run(
        "Get Joints Between",
        root_joint,
        end_joint,
    )

    if not host:
        host = mc.createNode("network")

    float_attrs = {
        "Stretch": 1,
        "SoftDistance": 0,
    }

    for idx, joint in enumerate(full_chain[1:]):
        float_attrs["Joint%sAddition" % idx] = 0
        float_attrs["Joint%sDefaultLength" % idx] = abs(mc.getAttr(f"{joint}.tx"))

    matrix_attrs = {
        "RootMatrix": None,
        "TargetMatrix": None,
    }

    aniseed_toolkit.run("Add Separator Attribute", host)

    for attr, value in float_attrs.items():
        mc.addAttr(
            host,
            shortName=attr,
            attributeType="float",
            keyable=False if "Default" in attr else True,
            defaultValue=value
        )

    # -- Convert the float to the attribute address
    for idx, joint in enumerate(full_chain):
        float_attrs["Joint%sAddition" % idx] = f"{host}.Joint%sAddition" % idx

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
        f"{root_target}.worldMatrix[0]",
        root_matrix,
    )

    mc.connectAttr(
        f"{end_target}.worldMatrix[0]",
        target_matrix,
    )

    last_attr = None
    for idx in range(len(full_chain) - 1):

        section_length = add(
            float_attrs["Joint%sDefaultLength" % idx],
            float_attrs["Joint%sAddition" % idx],
        )

        max_len_attr = add(
            section_length,
            last_attr or 0
        )

        last_attr = max_len_attr

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
    conditions = []

    # -_ FALSE TRACK
    for idx in range(len(full_chain) - 1):
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
        false_attr = add(
            float_attrs["Joint%sDefaultLength" % idx],
            float_attrs["Joint%sAddition" % idx],
        )


        mc.connectAttr(
            false_attr,
            f"{cond}.colorIfFalseR",
        )

        conditions.append(cond)

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
    # ------------------------------------------------

    # -- Add it all together
    for idx in range(len(full_chain) - 1):
        upper_attr = multiply(
            float_attrs["Joint%sDefaultLength" % idx],
            scale,
        )

        upper_attr = subtract(
            upper_attr,
            float_attrs["Joint%sDefaultLength" % idx]
        )

        upper_attr = multiply(
            upper_attr,
            stretch_attr,
        )

        upper_attr = add(
            upper_attr,
            float_attrs["Joint%sDefaultLength" % idx],
        )

        ##
        upper_attr = add(
            upper_attr,
            float_attrs["Joint%sAddition" % idx],
        )

        mc.connectAttr(
            upper_attr,
            f"{conditions[idx]}.colorIfTrueR",
        )

        multiplier = 1

        if facing_direction == facing_direction.NegativeX:
            multiplier = -1

        final_mul = multiply(
            f"{conditions[idx]}.outColorR",
            multiplier,
        )

        # -- Finally, conect the attributes to the joints
        mc.connectAttr(
            final_mul, #f"{conditions[idx]}.outColorR",
            f"{full_chain[idx + 1]}.translateX",
            force=True,
        )


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

