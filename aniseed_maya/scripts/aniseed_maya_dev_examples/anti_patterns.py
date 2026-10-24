"""
Common mistakes when writing aniseed components, each shown as a "don't"
and a "do".

This file is a reference to read. It is outside the components folder, so
aniseed never loads it, and nothing imports it. Each pair of functions shows
what the body of a component method might look like, with ``component``
standing in for ``self``.
"""
from maya import cmds
from maya.api import OpenMaya as om


# --------------------------------------------------------------------------------------
# 1. Changing the stack during a build
#
# The build works out which components to run before it starts. Adding or
# removing components from run means the change is missed, or half applied.
# Change the stack from on_enter_stack or a menu entry instead.
# See components/06_composite/ex14_add_child_components.py
# --------------------------------------------------------------------------------------
def dont_change_the_stack_in_run(component):
    component.rig.add_component(
        component_type="Dev Example : Simple Control",
        label="Added During Build",
    )


def do_change_the_stack_from_a_menu_entry(component):
    if component.rig.is_building():
        return

    component.rig.add_component(
        component_type="Dev Example : Simple Control",
        label="Added From The Menu",
        parent=component,
    )


# --------------------------------------------------------------------------------------
# 2. Putting API objects into outputs or options
#
# Outputs and options must hold plain values (strings, numbers, booleans, and
# lists and dictionaries of them). They are saved as json, shown in the app
# and read by other components. MObjects and MDagPaths cannot be saved, and
# stop being valid when the scene changes.
# See components/03_create/ex08_joint_chain_openmaya.py
# --------------------------------------------------------------------------------------
def dont_output_api_objects(component, joint_object: om.MObject):
    component.output("Root Joint").set(joint_object)


def do_output_names(component, joint_object: om.MObject):
    component.output("Root Joint").set(om.MFnDagNode(joint_object).partialPathName())


# --------------------------------------------------------------------------------------
# 3. Hard coding names
#
# Names belong to the rig's configuration. A hard coded name ignores the
# rig's naming convention and clashes the second time the component is used.
# See components/07_config/ex15_example_config.py
# --------------------------------------------------------------------------------------
def dont_hard_code_names():
    return cmds.createNode("transform", name="arm_ctrl")


def do_ask_the_configuration(component):
    return cmds.createNode(
        "transform",
        name=component.config.generate_name(
            classification=component.config.control,
            description="arm",
            location=component.config.left,
        ),
    )


# --------------------------------------------------------------------------------------
# 4. Using the selection in run
#
# The selection is whatever the user last clicked on, and there is no
# selection at all when a rig is built in mayapy. Everything run works on
# should come from inputs. The selection is fine in on_enter_stack and in
# menu entries, where the user is choosing something on purpose.
# --------------------------------------------------------------------------------------
def dont_use_the_selection_in_run():
    for node in cmds.ls(selection=True):
        cmds.setAttr(f"{node}.visibility", False)


def do_use_an_input(component):
    for node in component.input("Nodes").get():
        cmds.setAttr(f"{node}.visibility", False)


# --------------------------------------------------------------------------------------
# 5. Creating widgets or touching the ui outside option_widget/input_widget
#
# Widgets only exist while the app is showing the component, and never when a
# rig is built without the app. Create widgets only in option_widget and
# input_widget, and have run read option values, never widgets.
# See components/05_extending/ex12_custom_widget.py
# --------------------------------------------------------------------------------------
def dont_read_a_widget_in_run(component):
    return component.radius_widget.get_value()


def do_read_the_option(component):
    return component.option("Joint Radius").get()


# --------------------------------------------------------------------------------------
# 6. Doing work in __init__
#
# __init__ runs whenever the component is created: when it is added, when it
# is duplicated, and for every component whenever a recipe loads. Only
# declare inputs, options and outputs there. One-off setup belongs in
# on_enter_stack, and building belongs in run.
# See components/01_basics/ex04_lifecycle_logger.py
# --------------------------------------------------------------------------------------
def dont_create_nodes_in_init(component):
    # -- (imagine this inside __init__)
    component.guide = cmds.spaceLocator()[0]


def do_create_nodes_in_on_enter_stack(component):
    # -- (imagine this inside on_enter_stack)
    component.input("Guide").set(cmds.spaceLocator()[0])


# --------------------------------------------------------------------------------------
# 7. Hiding failures
#
# Catching every exception and returning True makes a broken build look like
# a successful one. Let unexpected errors raise, and return False (after
# logging why) only for failures you expected.
# See components/01_basics/ex03_validation.py
# --------------------------------------------------------------------------------------
def dont_hide_failures(component):
    try:
        cmds.parentConstraint(component.input("Driver").get(), component.input("Driven").get())
    except Exception:
        pass
    return True


def do_let_errors_raise(component):
    cmds.parentConstraint(component.input("Driver").get(), component.input("Driven").get())
    return True


# --------------------------------------------------------------------------------------
# 8. Changing an identifier
#
# The identifier is saved in every recipe which uses the component. Change it
# and those rigs load the component as a missing placeholder. If a component
# must be renamed, keep the old class (with deprecated = True) alongside the
# new one, or convert the data with migrate.
# See components/04_data/ex11_stored_values.py
# --------------------------------------------------------------------------------------
class DontRenameAnIdentifier:
    # -- Was "Dev Example : Simple Control" in every rig saved last year
    identifier = "Dev Example : Basic Control"


# --------------------------------------------------------------------------------------
# 9. Importing one component file from another
#
# Component files are loaded by their file path, not imported as modules,
# so they cannot import each other (and numbered folders such as 01_basics
# are not valid module names anyway). Put shared code in the package's mixins
# or widgets folder, which are importable by the package's name.
#
# Also note that the component library only loads files whose names start
# with a letter, which is why these files are called ex01_minimal.py and not
# 01_minimal.py. A file called 01_minimal.py would be silently skipped.
# See components/05_extending/ex13_using_a_mixin.py
# --------------------------------------------------------------------------------------
def dont_import_another_component_file():
    # -- This fails: 03_create is not a module
    # from aniseed_maya_dev_examples.components.03_create import ex09_simple_control
    pass


def do_import_from_the_mixins_or_widgets_folder():
    from aniseed_maya_dev_examples.mixins import LoggingMixin
    return LoggingMixin


# --------------------------------------------------------------------------------------
# 10. Changing the scene with OpenMaya without thinking about undo
#
# Changes made through OpenMaya do not go on Maya's undo queue, so undoing a
# build will not undo them. That is fine for nodes which are deleted and
# rebuilt every build, but use maya.cmds where a user may want to undo.
# See components/02_modify/ex06_lock_and_hide_openmaya.py
# --------------------------------------------------------------------------------------
def dont_forget_openmaya_changes_cannot_be_undone(plug: om.MPlug):
    plug.isLocked = True


def do_use_cmds_when_undo_matters(node: str, attribute_name: str):
    cmds.setAttr(f"{node}.{attribute_name}", lock=True)


# --------------------------------------------------------------------------------------
# 11. Checking wired inputs in is_valid
#
# is_valid runs before anything is built, so an input wired to another
# component's output has no value yet. Skip wired inputs in is_valid, and
# let run deal with them.
# See components/01_basics/ex03_validation.py
# --------------------------------------------------------------------------------------
def dont_check_wired_inputs_in_is_valid(component):
    return cmds.objExists(component.input("Joint").get())


def do_skip_wired_inputs_in_is_valid(component):
    joint_input = component.input("Joint")

    if joint_input.is_address():
        return True

    return cmds.objExists(joint_input.get())
