"""
Builds the showcase rig, which uses every dev example, and saves its recipe
to examples_showcase.json beside this file.

You only need this if you change the examples and want to update the
recipe. To try the examples, load examples_showcase.json instead (see the
package README).

From the Maya Script Editor (this replaces the current scene):

    import runpy
    runpy.run_path(r"<path to this file>", run_name="generate_showcase")

From mayapy:

    mayapy generate_showcase.py [output path]
"""
import os
import sys


def build_showcase_rig():
    """
    Opens a new scene and builds the showcase rig in it: the rig node, its
    groups and guides, and a stack using every dev example. Nothing is built.

    Returns:
        The aniseed.Rig
    """
    import aniseed
    from maya import cmds

    # -- The dev examples are off by default. Turn them on for this session
    # -- only, so the user's own choice (Edit > Packages) is left alone.
    aniseed.packages.set_enabled("aniseed_maya_dev_examples", True, persist=False)

    cmds.file(new=True, force=True)

    rig = aniseed.Rig(label="DevExampleRig")

    # -- suppress_events stops the configuration's on_enter_stack running,
    # -- which would otherwise add its own default stack
    rig.add_component(
        component_type="Rig Configuration : Dev Example",
        label="Configuration",
        suppress_events=True,
    )
    config = rig.config()

    def group(description, parent):
        name = config.generate_name(config.organisational, description, config.middle, unique=False)
        return cmds.createNode("transform", name=name, parent=parent)

    def guide(description, location, parent, position):
        # -- The guides are plain transforms, as the rig's recipe stores
        # -- transforms and joints, but not locator shapes. The Options And
        # -- Inputs example turns on their selection handles.
        name = config.generate_name(config.guide, description, location, unique=False)
        node = cmds.createNode("transform", name=name, parent=parent)
        cmds.xform(node, worldSpace=True, translation=position)
        return node

    guides_org = group("guides", rig.label)
    skeleton_org = group("skeleton", rig.label)
    controls_org = group("controls", rig.label)

    # -- Each chain gets its own pair of guides, so the chains do not overlap.
    # -- The chains lean slightly, so the orientation maths is exercised.
    guides = {
        "cmds_start": guide("chain_start", config.left, guides_org, (2, 10, 0)),
        "cmds_end": guide("chain_end", config.left, guides_org, (12, 12, 1)),
        "openmaya_start": guide("chain_start", config.right, guides_org, (-2, 10, 0)),
        "openmaya_end": guide("chain_end", config.right, guides_org, (-12, 12, 1)),
        "template_start": guide("template_start", config.middle, guides_org, (0, 2, 0)),
        "template_end": guide("template_end", config.middle, guides_org, (0, 2, 10)),
    }

    def add(component_type, label, parent, inputs=None, options=None):
        return rig.add_component(
            component_type=component_type,
            label=label,
            inputs=inputs,
            options=options,
            parent=parent,
        )

    build = add("Stack : Execution Block", "Build Rig", None)

    add("Utility : Delete Children", "Clear Skeleton", build, inputs={"Node": skeleton_org})
    add("Utility : Delete Children", "Clear Controls", build, inputs={"Node": controls_org})

    # -- 01 Basics
    basics = add("Stack : Organiser", "Basics", build)
    add("Dev Example : Minimal", "Minimal", basics)
    add(
        "Dev Example : Options And Inputs", "Show Guide Handles", basics,
        inputs={"Nodes": list(guides.values())},
        options={"Attribute Name": "displayHandle", "Value": 1.0},
    )
    add(
        "Dev Example : Validation", "Validation", basics,
        inputs={"Node": guides_org},
    )
    add("Dev Example : Lifecycle Logger", "Lifecycle Logger", basics)

    # -- 03 Create (built before 02 Modify, as the modifiers need its nodes)
    create = add("Stack : Organiser", "Create", build)
    add(
        "Dev Example : Joint Chain (cmds)", "Joint Chain (cmds)", create,
        inputs={"Start": guides["cmds_start"], "End": guides["cmds_end"], "Parent": skeleton_org},
        options={"Location": config.left},
    )
    add(
        "Dev Example : Joint Chain (OpenMaya)", "Joint Chain (OpenMaya)", create,
        inputs={"Start": guides["openmaya_start"], "End": guides["openmaya_end"], "Parent": skeleton_org},
        options={"Location": config.right},
    )
    add(
        "Dev Example : Simple Control", "Simple Control", create,
        inputs={"Parent": controls_org, "Joint to Drive": "[Joint Chain (cmds)].[output].[Root Joint]"},
        options={"Location": config.left},
    )
    add(
        "Dev Example : Utility Network", "Utility Network", create,
        inputs={
            "Start": "[Simple Control].[output].[Control]",
            "End": guides["openmaya_end"],
            "Driven Node": "[Joint Chain (OpenMaya)].[output].[Root Joint]",
        },
        options={"Location": config.right},
    )

    # -- 02 Modify
    modify = add("Stack : Organiser", "Modify", build)
    add(
        "Dev Example : Colour Nodes (cmds)", "Colour Nodes (cmds)", modify,
        inputs={"Nodes": "[Simple Control].[output].[Control]"},
    )
    add(
        "Dev Example : Lock And Hide (OpenMaya)", "Lock And Hide (OpenMaya)", modify,
        inputs={"Nodes": "[Joint Chain (OpenMaya)].[output].[Joints]"},
        options={"Attributes": ["translate", "rotate", "visibility"]},
    )

    # -- 04 Data and 05 Extending
    data = add("Stack : Organiser", "Data And Extending", build)
    stored_values = add(
        "Dev Example : Stored Values", "Stored Values", data,
        inputs={"Nodes": "[Simple Control].[output].[Control]"},
        options={"Attributes": ["translateY"]},
    )
    # -- As if Capture had been pressed with the control raised 2 units,
    # -- which the Utility Network then turns into a stretch
    control_name = config.generate_name(config.control, "demo", config.left, unique=False)
    stored_values.option("_Stored Values").set({control_name: {"translateY": 2.0}})

    add(
        "Dev Example : Custom Widget", "Custom Widget", data,
        inputs={"Joints": "[Joint Chain (cmds)].[output].[Joints]"},
        options={"Joint Radius": 2.0},
    )
    add(
        "Dev Example : Using A Mixin", "Using A Mixin", data,
        inputs={"Nodes": "[Joint Chain (cmds)].[output].[Joints]"},
    )

    # -- 06 Composite. Adding it the normal way runs its on_enter_stack, which
    # -- adds and wires its children.
    composite = add("Stack : Organiser", "Composite", build)
    add(
        "Dev Example : Add Child Components", "Template", composite,
        inputs={
            "Start Guide": guides["template_start"],
            "End Guide": guides["template_end"],
            "Skeleton Parent": skeleton_org,
            "Control Parent": controls_org,
        },
    )

    # -- 08 Publish. Disabled, as publishing writes files: enable it and set
    # -- the folders to try it.
    publish = add("Stack : Organiser", "Publish (enable to try)", build)
    add("Dev Example : Save Scene Version", "Save Scene Version", publish)
    add(
        "Dev Example : Publish Rig", "Publish Rig", publish,
        inputs={"FBX Roots": [skeleton_org], "Nodes To Delete": [controls_org]},
    )
    publish.set_enabled(False)

    return rig


def save_showcase(path=None):
    """
    Builds the showcase rig and saves its recipe.

    Args:
        path: Where to save the recipe. Defaults to examples_showcase.json
            beside this file.

    Returns:
        The path the recipe was saved to.
    """
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples_showcase.json")

    rig = build_showcase_rig()
    rig.save(path)

    return path


def _initialise_mayapy():
    """
    Starts Maya in mayapy and makes aniseed importable, assuming this file is
    in its usual place in the aniseed checkout.
    """
    import maya.standalone
    maya.standalone.initialize()

    scripts = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    vendor = os.path.join(os.path.dirname(scripts), "vendor", "scripts")

    for path in (scripts, vendor):
        if path not in sys.path:
            sys.path.insert(0, path)


if __name__ == "__main__":
    _initialise_mayapy()
    print(f"Saved {save_showcase(sys.argv[1] if len(sys.argv) > 1 else None)}")

elif __name__ == "generate_showcase":
    print(f"Saved {save_showcase()}")
