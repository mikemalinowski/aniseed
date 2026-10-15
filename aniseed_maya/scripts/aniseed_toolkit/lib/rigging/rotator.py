import mref

from .. import constraints


def create_rotator(target_a, target_b, match_to, parent, description, location, config) -> str:
    """
    This will create a transform which blends rotation between two nodes. The
    transform is given a "Blend" attribute, where 0 follows target_a and 1
    follows target_b.

    Args:
        target_a: The first node to blend between
        target_b: The second node to blend between
        match_to: The node to match the transform of the rotator to
        parent: The node to parent the rotator under
        description: The description to use when naming the rotator
        location: The location to use when naming the rotator
        config: The rig configuration

    Returns:
        The name of the rotator transform
    """
    rotator_node = mref.create(
        "transform",
        parent=parent,
    )
    rotator_node.rename(
        config.generate_name(
            classification="mech",
            description=description,
            location=location,
        ),
    )
    rotator_node.match_to(match_to)

    blend_attribute = rotator_node.add_attribute(
        "Blend",
        value=0.5,
        attribute_type="float",
        keyable=True,
    )

    mref.parentConstraint(
        target_a,
        rotator_node,
        maintainOffset=True,
    )

    constraint = mref.parentConstraint(
        target_b,
        rotator_node,
        maintainOffset=True,
    )[0]
    constraint.attr("interpType").set(0)  # No Flip

    constraints.blend_weights(blend_attribute, constraint)

    return rotator_node.name()
