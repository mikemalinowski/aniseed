# aniseed_maya_dev_examples

Documented example components for developers learning to write aniseed
components in Maya. They go from the smallest component aniseed can build, up
to components which create nodes, store data, use mixins, add other
components and publish files.

Every example is written to be read. The docstrings and `# --` comments
explain *why*, as well as *what*, and each file starts with a "What this
example teaches" list and a "Read next" pointer.

All of the components are listed under **Dev Example** in the component
library, apart from the configuration, which is listed as
**Rig Configuration : Dev Example**.

## Rules the examples follow

* **No `aniseed_toolkit`, no `mref`, no `crosswalk`.** Each example uses only
  `aniseed`, `maya.cmds` and/or `maya.api.OpenMaya` (and `Qt` for widgets), so
  it shows exactly what a component needs.
* The cmds examples import no OpenMaya, and the OpenMaya examples import no
  cmds, so the two APIs can be compared fairly.
* Nothing imports from `aniseed_maya_standard`. The package only requires it
  because it provides the Maya host (menu, docking, undo).

## Reading order

| #  | File | Identifier | Teaches |
|----|------|------------|---------|
| 01 | `components/01_basics/ex01_minimal.py` | Dev Example : Minimal | The minimum: an identifier and `run` |
| 02 | `components/01_basics/ex02_options_and_inputs.py` | Dev Example : Options And Inputs | Inputs vs options, `.get()`, groups, `pre_expose` |
| 03 | `components/01_basics/ex03_validation.py` | Dev Example : Validation | `is_valid`, required inputs, `return False` vs raising |
| 04 | `components/01_basics/ex04_lifecycle_logger.py` | Dev Example : Lifecycle Logger | Every hook, and when it is called |
| 05 | `components/02_modify/ex05_colour_nodes_cmds.py` | Dev Example : Colour Nodes (cmds) | A modifier in maya.cmds, `option_widget` |
| 06 | `components/02_modify/ex06_lock_and_hide_openmaya.py` | Dev Example : Lock And Hide (OpenMaya) | A modifier in OpenMaya, plugs, the undo caveat |
| 07 | `components/03_create/ex07_joint_chain_cmds.py` | Dev Example : Joint Chain (cmds) | Creating nodes, outputs, naming through the config |
| 08 | `components/03_create/ex08_joint_chain_openmaya.py` | Dev Example : Joint Chain (OpenMaya) | The same as 07 with `MDagModifier` (diff the two) |
| 09 | `components/03_create/ex09_simple_control.py` | Dev Example : Simple Control | A real rig component: addresses, `hook_to_parent`, default outputs |
| 10 | `components/03_create/ex10_utility_network.py` | Dev Example : Utility Network | DG nodes, connections, outputting an attribute |
| 11 | `components/04_data/ex11_stored_values.py` | Dev Example : Stored Values | Buttons, menus, hidden options, `on_serialise`, `version` + `migrate` |
| 12 | `components/05_extending/ex12_custom_widget.py` | Dev Example : Custom Widget | Writing your own option widget |
| 13 | `components/05_extending/ex13_using_a_mixin.py` | Dev Example : Using A Mixin | Mixins and `mixin_functions` |
| 14 | `components/06_composite/ex14_add_child_components.py` | Dev Example : Add Child Components | Adding and wiring components from code |
| 15 | `components/07_config/ex15_example_config.py` | Rig Configuration : Dev Example | A naming configuration, and a default stack |
| 16 | `components/08_publish/ex16_save_scene_version.py` | Dev Example : Save Scene Version | Saving versioned scenes |
| 17 | `components/08_publish/ex17_publish_rig.py` | Dev Example : Publish Rig | Publishing: checks, cleanup on a copy, FBX, recipe, manifest |
| —  | `anti_patterns.py` | — | Common mistakes, as "don't" / "do" pairs |

Shared code lives in two importable folders:

* `mixins/logging_mixin.py`: `LoggingMixin`, used by #13
* `widgets/slider_spin_box.py` and `widgets/folder_selector.py`: used by #12, #16 and #17

## Turning the examples on

The examples are **off by default** (`"enabled_by_default": false` in
`aniseed_package.json`), so they do not appear in the component library of
riggers who do not need them. To turn them on, open the aniseed app, choose
**Edit > Packages...**, and tick **aniseed_maya_dev_examples**. The change
takes effect straight away and is remembered.

## Try it

### The playground

Create a new rig and choose **Rig Configuration : Dev Example** as its
configuration. The rig starts with two guide locators and a "Build Rig" block
which builds a joint chain along them and a control to drive it. Move the
guides and build again.

### The showcase

`recipes/examples_showcase.json` is a rig that uses every example, wired
together:

* the two joint chains are built side by side from their own guides
* the Simple Control drives the cmds chain, and its colour comes from the
  Colour Nodes example
* the Utility Network stretches the OpenMaya chain as the control moves away
  from the chain's end guide
* Stored Values raises the control by 2 units on every build, as if Capture
  had been pressed with it there
* the Template adds and wires its own chain and control
* the publish components are in a disabled "Publish (enable to try)" group

To load it, open a new scene, open the Aniseed app, and open
`recipes/examples_showcase.json` with the app's open/load option. Then press
**Build Rig**. Watch the Script Editor, as the Lifecycle Logger and Using A
Mixin examples log what they do.

The guides in the showcase are plain transforms rather than locators, because
the recipe stores transforms and joints but not locator shapes. The Options
And Inputs example ("Show Guide Handles") turns on their selection handles so
you can see and select them.

To try publishing, enable "Publish (enable to try)", set the Output Folder of
Save Scene Version and the Publish Root of Publish Rig, then build.

If you change the examples, run `recipes/generate_showcase.py` to rebuild the
recipe (see its docstring).

## Things worth knowing

* **File names must start with a letter.** The component library skips any
  file whose name starts with anything else, which is why the files are called
  `ex01_minimal.py` rather than `01_minimal.py`. Numbered folders are fine.
* **Component files cannot import each other.** They are loaded by file path,
  so put shared code in the package's `mixins/` or `widgets/` folders.
* **Labels must not contain a full stop.** Addresses such as
  `[Simple Control].[output].[Control]` are split on full stops.
* **`on_enter_stack` does not run when a recipe loads.** Use it for one-off
  setup when the user adds a component.
* **An exception in `on_build_finished` does not fail the build.** It is only
  logged, because the build has already finished.
* **OpenMaya changes cannot be undone.** Undoing a build undoes everything
  done through maya.cmds, but nothing done through OpenMaya.

## Building headlessly

The examples build in mayapy with no UI. Widgets are only created by the
app. To create widgets in mayapy (for tests, say), create a
`QtWidgets.QApplication` *before* calling `maya.standalone.initialize()`.
Otherwise Maya creates a `QGuiApplication`, which cannot host widgets, and
creating any widget crashes the interpreter.
