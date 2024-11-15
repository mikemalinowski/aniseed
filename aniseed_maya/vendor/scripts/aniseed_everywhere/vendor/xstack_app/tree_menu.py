from .vendor import qute
import functools
import collections

# --------------------------------------------------------------------------------------
def construct(menu_dict, icon_dict, tree_item, app_config, stack):

    construct_defaults(menu_dict, icon_dict, app_config)

    if hasattr(tree_item, "uuid_"):
        construct_component_menu(
            component=stack.component(tree_item.uuid_),
            item=tree_item,
            menu_dict=menu_dict,
            icon_map=icon_dict,
            app_config=app_config,
        )

    else:
        construct_blank_selection_menu(
            stack=stack,
            item=tree_item,
            menu_dict=menu_dict,
            icon_map=icon_dict,
            app_config=app_config,
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def construct_defaults(
        menu_dict: collections.OrderedDict[str, callable],
        icon_map: dict,
        app_config,
):

    # -- Determine what our label strings are
    component_label = app_config.component_label
    execute_label = app_config.execute_label

    # -- Construct our default
    menu_dict[execute_label] = collections.OrderedDict()
    menu_dict["Validate"] = collections.OrderedDict()
    execute_types = [execute_label, "Validate"]

    # -- Get the icons from the config
    validate_icon = qute.QIcon(app_config.validate_icon)
    execute_icon = qute.QIcon(app_config.execute_icon)

    # -- Build the default icon map, so our standard labels are all
    # -- iconised
    icon_map = {
        "Validate": app_config.validate_icon,
        execute_label: app_config.execute_icon,
        f"Add {app_config.component_label}": app_config.add_icon,
        f"Remove {app_config.component_label}": app_config.remove_icon,
        f"Duplicate {app_config.component_label}": app_config.duplicate_icon,
    }


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def construct_blank_selection_menu(
        stack,
        item,
        menu_dict: collections.OrderedDict[str, callable],
        icon_map: dict,
        app_config,
):
    if not item:
        return

    tree = item.treeWidget()
    component_label = app_config.component_label
    execute_label = app_config.execute_label

    validate_icon = qute.QIcon(app_config.validate_icon)
    execute_icon = qute.QIcon(app_config.execute_icon)

    execute_types = [execute_label, "Validate"]

    for execute_type in execute_types:

        validate_only = execute_type == "Validate"

        icon_to_use = validate_icon if validate_only else execute_icon

        menu_dict[execute_type][
            f"{execute_type} {app_config.label}"] = functools.partial(
            stack.build,
            validate_only=validate_only,
        )
        icon_map[f"{execute_type} {app_config.label}"] = icon_to_use

    _add_separator(menu_dict)

    menu_dict[f"Add {app_config.component_label}"] = functools.partial(
        tree.add_component,
        parent_uuid=None
    )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def construct_component_menu(
        component,
        item,
        menu_dict: collections.OrderedDict[str, callable],
        icon_map: dict,
        app_config,
):
    # -- Get the tree widget
    tree = item.treeWidget()

    # -- Get our labels from the config - this allows the developer
    # -- to tailor the users experience
    component_label = app_config.component_label
    execute_label = app_config.execute_label

    # -- We allow the same mechanisms whether you are validating
    # -- or executing, so we need to build this part twice
    execute_types = [execute_label, "Validate"]

    # -- Determine our icons
    validate_icon = qute.QIcon(app_config.validate_icon)
    execute_icon = qute.QIcon(app_config.execute_icon)

    for execute_type in execute_types:

        # -- Check if we are validating
        validate_only = execute_type == "Validate"
        icon_to_use = validate_icon if validate_only else execute_icon

        menu_dict[execute_type][f"{execute_type} Section"] = functools.partial(
            component.stack.build,
            build_below=component.uuid(),
            validate_only=validate_only,
        )

        _add_separator(menu_dict[execute_type])

        icon_map[f"{execute_type} Section"] = icon_to_use

        menu_dict[execute_type][f"{execute_type} Up To This"] = functools.partial(
            component.stack.build,
            build_up_to=component.uuid(),
            validate_only=validate_only,
        )
        icon_map[f"{execute_type} Up To This"] = icon_to_use

        menu_dict[execute_type][f"{execute_type} Just this"] = functools.partial(
            component.stack.build,
            build_only=component.uuid(),
            validate_only=validate_only,
        )
        icon_map[f"{execute_type} Just this"] = icon_to_use

    _add_separator(menu_dict)

    # -- Now add our manipulation functions
    menu_dict[f"Rename {app_config.component_label}"] = functools.partial(
        tree.rename_component,
        item
    )

    _add_separator(menu_dict)

    menu_dict[f"Add {app_config.component_label}"] = functools.partial(
        tree.add_component,
        parent_uuid=component.uuid()
    )

    menu_dict[f"Remove {app_config.component_label}"] = functools.partial(
        tree.remove_component,
        item,
    )

    menu_dict[f"Duplicate {app_config.component_label}"] = functools.partial(
        tree.duplicate_component,
        item,
    )

    # -- Create the user functions menu
    additional_actions_menu = collections.OrderedDict()

    construct_additional_actions(
        component,
        item,
        additional_actions_menu,
        icon_map,
        app_config,
    )

    menu_dict["Actions"] = additional_actions_menu

    # -- Now add the help menu
    _add_separator(menu_dict)

    menu_dict[f"Help"] = functools.partial(
        tree.help_for_component,
        item
    )

# --------------------------------------------------------------------------------------
def construct_additional_actions(
        component,
        item,
        menu_dict: collections.OrderedDict[str, callable],
        icon_map: dict,
        app_config,
):

    # -- Get the tree widget
    tree = item.treeWidget()

    menu_dict["Enable/Disable"] = functools.partial(
        tree.toggle_enable,
        item,
    )

    # -- We add a menu that allows the user to select different versions if
    # -- the component has multiple versions
    versions = component.stack.component_library.versions(component.identifier)

    if len(versions) > 1:

        version_menu = collections.OrderedDict()

        # -- Add the option to make the component always use latest
        version_menu[f"Always Use Latest"] = functools.partial(
            tree.switch_version,
            item,
            None,
        )

        for version in versions:
            version_menu[f"Switch To {version}"] = functools.partial(
                tree.switch_version,
                item,
                version,
            )

        # -- Add a sub menu to nest all the versions under
        menu_dict["Force Version"] = version_menu

    # -- Add the export/import  settings options
    _add_separator(menu_dict)

    menu_dict["Export Settings"] = functools.partial(
        tree.save_component_settings,
        item,
    )

    menu_dict["Import Settings"] = functools.partial(
        tree.load_component_settings,
        item,
    )

    # -- Now we will add the menu items from the component
    _add_separator(menu_dict)

    for label, func_ in component.user_functions().items():
        menu_dict[f"{label}"] = func_


# --------------------------------------------------------------------------------------
def _add_separator(menu_dict):

    sep_count = 0

    for key in menu_dict.keys():
        if key.startswith("-"):
            sep_count += 1

    menu_dict["-" * (sep_count + 1)] = None