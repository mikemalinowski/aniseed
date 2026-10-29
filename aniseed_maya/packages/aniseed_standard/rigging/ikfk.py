"""
Helpers shared by the components which blend between an ik and an fk
setup.
"""
import mref

import aniseed_utilities as au


def create_ikfk_visibility(
        attribute,
        ik_controls: list[str],
        fk_controls: list[str],
        ik_threshold: float = 0.9,
        fk_threshold: float = 0.1,
):
    """
    Drives the visibility of the ik and fk controls from an ikfk blend
    attribute (where 0 is ik and 1 is fk). The ik controls are visible
    whilst the blend is below the ik threshold and the fk controls are
    visible whilst the blend is above the fk threshold, so both are visible
    mid-blend.

    The visibility is driven on the offset node of each control.

    Args:
        attribute: The ikfk blend attribute
        ik_controls: The controls to show when in ik
        fk_controls: The controls to show when in fk
        ik_threshold: The ik controls are visible below this value
        fk_threshold: The fk controls are visible above this value
    """
    attribute = mref.get(attribute)

    ik_condition = mref.create("lessThan")
    fk_condition = mref.create("greaterThan")

    attribute.connect(ik_condition.input1)
    attribute.connect(fk_condition.input1)

    ik_condition.input2.set(ik_threshold)
    fk_condition.input2.set(fk_threshold)

    for condition, controls in ((ik_condition, ik_controls), (fk_condition, fk_controls)):
        for control in controls:
            off = au.rig.control.get(control).off
            condition.attr("output").connect(f"{off}.visibility", force=True)


def create_snap_groups(label: str, prefix: str, location: str, ikfk_attribute: str) -> tuple[str, str, str]:
    """
    Declares the three snappy groups used for ik/fk matching and stores
    the ikfk attribute on them.

    Args:
        label: The label of the limb type, e.g. "Arm"
        prefix: The descriptive prefix of the component
        location: The location of the component
        ikfk_attribute: The address of the ikfk blend attribute

    Returns:
        The ikfk, ik only and fk only group names
    """
    # -- snappy is imported here as its package also imports its (Qt) ui
    import snappy

    ikfk_group = f"IKFK_{label}_{prefix}_{location}"
    ikonly_group = f"IKOnly_{label}_{prefix}_{location}"
    fkonly_group = f"FKOnly_{label}_{prefix}_{location}"

    snappy.set_data(
        data_name="ikfk_attribute",
        data_value=ikfk_attribute,
        group=[ikfk_group, fkonly_group, ikonly_group],
    )

    return ikfk_group, ikonly_group, fkonly_group
