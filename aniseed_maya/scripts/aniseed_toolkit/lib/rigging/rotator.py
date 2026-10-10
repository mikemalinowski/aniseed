import mref


def create_rotator(target_a, target_b, match_to, parent, description, location, config) -> mref.ReferencedItem:
    """
    This will create a transform which blends rotation between two nodes
    Args:
        target_a:
        target_b:
        match_to:
        parent:
        description:
        location:
        config:

    Returns:

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

    constraint = mref.get(
        mref.parentConstraint(
            target_b,
            rotator_node,
            maintainOffset=True,
        )[0]
    )
    constraint.attr("interpType").set(0)  # No Flip

    weight_attributes = constraint.weight_attributes()

    reverse_node = mref.create("reverse")
    blend_attribute.connect(reverse_node.attr("inputX"))
    reverse_node.attr("outputX").connect(weight_attributes[0])
    blend_attribute.connect(weight_attributes[1])

    return rotator_node.name()
