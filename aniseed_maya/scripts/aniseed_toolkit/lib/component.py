from maya import cmds

from . import mirror as _mirror


def mirror(component_instance, transforms, location_label, config, joint_parent=None, input_overrides=None, option_overrides=None):
    original_location = component_instance.option(location_label).get()

    if original_location not in [config.left, config.right]:
        print("You can only mirror if the component is left or right")
        return

    # -- Get the opposite location
    new_location = config.left if original_location == config.right else config.right

    # -- Select the parent joint and duplicate ourselves (setting hte label so
    # -- we know its mirrored. Note that we clear the root bone as this will
    # -- trigger the duplcated component to generate the skeleton too.
    if joint_parent:
        cmds.select(joint_parent)

    option_overrides = option_overrides or dict()
    option_overrides.update({location_label: new_location})

    mirrored_component = component_instance.duplicate(
        input_overrides=input_overrides or dict(),
        option_overrides=option_overrides,
    )
    mirrored_component.set_label(f"{component_instance.label()} (Mirrored)")

    # -- Now we do an in-place mirror
    _mirror.global_mirror(
        transforms=transforms,
        name_replacement=[
            config.resolved_location(original_location),
            config.resolved_location(new_location),
        ],
    )