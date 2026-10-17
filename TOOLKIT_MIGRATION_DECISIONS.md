# aniseed_toolkit migration: decisions log

Decisions made while carrying out TOOLKIT_MIGRATION_PLAN without the owner
available. Each entry records what was chosen, why, and the alternatives, so any
of them can be revisited later.

Work happens on the local git branch `toolkit-restructure`. Nothing is pushed.
Commits are made per phase (and per fix where useful), so each can be reverted
on its own.


## D0. Version control

- **Chosen:**
  - Git is not on PATH, so the git bundled with GitHub Desktop is used.
  - A new branch `toolkit-restructure` was created from `main`. Its first commit
    contains the earlier component cleanup.
  - Only `aniseed_maya/scripts/aniseed`, `aniseed_maya/scripts/aniseed_toolkit` and
    the plan/decision files are ever staged.
- **Why:**
  - The uncommitted changes under `aniseed_maya/vendor` (mref) and the untracked
    `colorcast` folder are the owner's own pending work, so they are left untouched
    and unstaged.
  - `__pycache__` folders are never staged.
- **Alternatives:**
  - Commit directly on `main`.
  - Squash everything into one commit at the end.


## D1. Removed code stays importable (phase 1)

- **Chosen:**
  - Dead or broken public names are moved out of the public modules into
    `aniseed_toolkit/_legacy` instead of being deleted. They are served on demand
    through a module level `__getattr__` and log one DeprecationWarning per name.
    - guide.create_ik_guide (unused)
    - guide.create_multi (broken, always returned None)
    - transformation.TransformMixerUi (empty stub)
    - rigging.TransformMixer / rigging.transform_mixer (unused)
  - Removal is planned for 4.0.
- **Why:** the plan promises that every existing import path keeps working, and
  owner scripts may reference these names.
- **Alternatives:**
  - Delete outright now.
  - Keep them in place with a deprecation comment.


## D2. control.create with no shape (phase 1)

- **Chosen:** if `shape` is empty, no shape is applied.
- **Why:**
  - Previously, an empty shape made the "Apply Shape" tool open a shape picker
    dialog in the middle of a build (and it applied the result to whatever was
    selected).
  - Library code must not prompt. Every existing caller passes a shape.
- **Alternatives:**
  - Raise a ValueError for an empty shape.
  - Apply a default shape (e.g. core_cube).


## D3. control.create with no match_to (phase 1)

- **Chosen:** each node of the control is explicitly re-matched to its own world
  matrix.
- **Why:**
  - That is exactly what the old code did implicitly (`xform(None)` queried the
    selection, which was the node itself).
  - Keeping it guarantees byte-identical scenes (verified by the rig harness)
    while removing the dependency on the selection.
- **Alternatives:** skip the matching entirely when match_to is None. This is
  cleaner, but could introduce floating point noise in the local transform values
  compared to existing rigs.
- **Note (phase 6):** in practice the control is left at the world origin, not at
  its parent. The nodes are created at the origin and parented absolutely
  (`set_parent`), so they keep that world transform. The control.create
  docstring now says this. The plan's earlier wording ("leave at the parent") was
  inaccurate.

## D4. Fixing the broken library functions (phase 1, open decision 1)

- **Chosen:** fixed, one commit each, so each fix can be reverted on its own.
  - tagging.find_all
  - visibility.hide and visibility.show
  - Direction.set_direction
  - joints.replicate_chain with replacements
  - skin.load return value
  - pinning.pin shape and colour
- **Details:**
  - pinning.pin now uses red (255, 0, 0) for the pin shapes. The code passed r=1
    to a function that works in 0-255, which is clearly meant as red.
  - Direction.set_direction now accepts "x", "Positive X", "Negative X" and "-x"
    style strings, and keeps NegativeZ as 6.
- **Why:** each one either raised or returned a wrong result on every call, so no
  working behaviour can depend on them.
- **Alternatives:**
  - Leave the bugs and only document them.
  - For the pin colour, use another colour or a darker red.


## D5. Shape tools and their node argument (phase 1)

- **Chosen:** Apply Shape, Rotate/Offset/Scale Shapes and Apply Shape Color act on
  the given node, and only fall back to the selection when no node is given.
- **Why:**
  - They documented a node argument but always ignored it.
  - This was why "Load Rig Control Shapes From File" applied every stored shape
    to the current selection.
- **Alternatives:** keep the tools selection-only and remove the node argument.


## D6. Misspelled tool identifier (phase 2)

- **Chosen:** the "Get Upvector Direction" tool declared `identifer` (sic), so it
  was registered with an empty identifier. It is now registered as "Get Upvector
  Direction".
- **Why:** a tool with an empty identifier cannot be used deliberately.
- **Alternatives:** none sensible.


## D7. Which wrapper tools become @tool functions (phase 2)

- **Chosen:**
  - 41 of the 64 thin wrapper tools had exactly the library function's signature
    and no class customisation. They were replaced by `@tool(...)` on the library
    function, with the same identifier, version, flags and categories (the tool
    registry snapshot proves it).
  - The other 23 stay as Tool classes because they declare ui_elements (custom
    widgets), different parameter defaults/names, or wrap a class. Making those
    functions would change the forms users see in the toolkit ui.
  - The documentation the toolkit shows for a converted tool is now the library
    function's docstring.
- **Alternatives:**
  - Give @tool a `ui_elements` hook and an `adapter` signature, then convert the
    remaining 23 as well.
  - Keep all 64 wrapper classes.

## D8. aniseed_toolkit.rig.get keeps a deferred aniseed import (phase 3)

- **Chosen:**
  - `rig.controls.get` (old `aniseed_toolkit.rig.get`) imports aniseed inside the
    function.
  - The toolkit can be imported and used without aniseed. Only `get`,
    `opposing_controls` and `controls_by_location` need aniseed when called.
- **Why:**
  - Those functions need the rig's configuration to work out sides and names,
    and they are themselves tools ("Get Opposites", "Get By Location").
  - Moving them into aniseed would move tools out of the toolkit.
- **Alternatives:**
  - Move all three into aniseed and register the tools from there.
  - Pass the config in explicitly (a signature change).


## D9. "Use the selection when no argument is given" (phase 3)

- **Chosen:**
  - Library functions keep their existing behaviour of falling back to the
    selection when an argument is omitted, e.g. `visibility.hide()` or
    `distance_between()`.
  - The rule that is enforced is that there is no hidden selection dependency:
    when arguments are given, the result never depends on the selection. The
    lib-to-tool calls and the selection-only shape tools that broke this are
    gone.
- **Why:** removing the fallbacks would change the behaviour of dozens of public
  functions and of the tool forms built from them.
- **Alternatives:** remove every fallback from the library and do the selection
  resolution only in the tools layer. This is cleaner, but it breaks scripts
  that call these functions without arguments.


## D10. Wrapper tools that transformed their arguments (phase 2 fix, found in phase 3)

- **What happened:**
  - Nine of the converted wrappers did more than forward their arguments.
  - Eight substituted the selection for an empty argument: Create Pins,
    Remove Pins, Pin Hierarchy, Get Joint From Pin, Get Pin From Node,
    Get By Location, Invert Translation and Serialise Nodes To Dict.
  - Direction Between forced print_result=True.
- **How it was found:** the phase 2 conversion compared signatures only. The
  toolkit behaviour harness caught the change.
- **Chosen:** those nine are @tool functions in their tools modules, recreated
  from the original run() bodies. The library functions are no longer
  decorated.
- **Alternatives:** keep them as Tool classes.


## D11. Version and history (phase 3)

- **Chosen:**
  - The package version is now 3.1.0 (new layout plus deprecations, still
    backwards compatible).
  - Code was moved by a script (scratch tooling, not committed), so the moved
    code is byte for byte the original apart from rewritten references.
  - The old lib modules are replaced by shims in the same commit. That keeps
    every commit runnable, at the cost of git not recording the moves as
    renames; `git blame -C -C` / `git log --follow` still trace the code.
- **Alternatives:**
  - Split the move into a non-runnable "pure move" commit followed by a shim
    commit, for cleaner rename detection.
  - Bump to 4.0.0.


## D12. Where the moved component support lives (phase 3/5, open decision 2)

- **Chosen:**
  - aniseed.builders: add_space_switch, setup_fk_*_switches, mirror_component,
    add_twister, create_joint_from_selection.
  - aniseed.dialogs: request_count and the option file dialogs.
  - aniseed.component_outputs.
  - ~~aniseed.mixins: JointChainMixin, InsertControlMixin and
    SingularControlMixin, alongside MirrorMixin.~~ Superseded by D23: those
    three mixins were removed and MirrorMixin is the only mixin.
  - The FacialControlRig stayed in the toolkit (rigging.facial) because it has no
    aniseed dependency.
- **Alternatives:**
  - Different module names (e.g. aniseed.component_helpers).
  - Make component_outputs methods on RigComponent.

## D13. Interactive versions of library functions (phase 4)

- **Chosen:**
  - `scene.mirror.mirror_transforms` and the `scene.hierarchy_io` file read/write
    functions never prompt. A missing name replacement means "no rename", and
    the file functions require a filepath.
  - The prompting versions (identical to the old behaviour) are
    `ui.dialogs.global_mirror`, `ui.dialogs.write_hierarchy_file` and
    `ui.dialogs.load_hierarchy_file`.
  - The old paths (`aniseed_toolkit.mirror.global_mirror`,
    `aniseed_toolkit.io.*_hierarchy_file`) and the tools resolve to the prompting
    versions, so nothing changes for callers.
- **Why:** library code must not open dialogs, but scripts and tools relying on
  the prompts must keep working.
- **Alternatives:**
  - Keep the prompts in the library behind an `interactive=True` flag.


## D14. The tool box is created on first use (phase 4)

- **Chosen:** `aniseed_toolkit.tools` / `ToolBox.singleton()` / `run()` create the
  tool box when first needed, not when the package is imported.
- **Why:**
  - Creating it executes every tool module, and many import Qt/qtility.
  - Creating it lazily means the library (core, scene, rig, rigging) can be
    imported and used without Qt. This is checked by a test which blocks
    every Qt/qtility import.
  - The tool box re-assigns `aniseed_toolkit.tools` to itself after loading
    tools, because importing tool modules can shadow that name with the tools
    folder as a namespace package.
- **Alternatives:** create it at import time as before (simpler, but it ties the
  whole package to Qt).


## D15. Third party imports which pull in Qt (phase 4)

- **Chosen:** `snappy` is imported inside `rigging.ikfk.create_snap_groups`
  rather than at module level, because snappy's package init imports its Qt ui.
- **Alternatives:** change snappy so its package init does not import its ui.
  That is a better fix, but it is in another package.

## D16. Names and split of the moved rig builders (phase 4b)

- **Chosen:**
  - The builders behind the tools Create Twist Setup, Create Spline Setup,
    Create Ribbon (ribbon2), Create Aim Hierarchy (guide_follow) and Align Bones
    For Ik now live in `rigging.twist`, `rigging.spline`, `rigging.ribbon`,
    `rigging.aim_hierarchy` and `rigging.bone_alignment`.
  - They are exposed as `create_twist_setup`, `create_spline_setup`,
    `create_ribbon`, `create_aim_hierarchy` and `align_bones_for_ik`. These
    follow the existing `create_*` naming.
  - The tools are now thin. They keep their identifiers, signatures and
    selection fallbacks, and their module-level class aliases (`TwistSetup`,
    `SimpleSplineSetup`, `Ribbon`).
  - For Align Bones For Ik:
    - The tool keeps the selection fallback, the prompts and the selection
      restore.
    - The library function takes every value explicitly.
- **Why:** library code must not depend on selection or prompts (plan, section 1).
- **Alternatives:**
  - Name the modules after the tools (`rigging.guide_follow`, `rigging.ik_alignment`).
  - Expose the classes only, with no `create_*` functions.


## D17. Re-pinning in Align Bones For Ik (phase 4b)

- **Chosen:** the library re-pins joints only when some were pinned before.
  - The old `run("Create Pins", [])` call fell back to the selection.
  - By that point the selection only contains replicated joints which have
    already been deleted, so the observable result is identical.
  - The harness case confirms this.
- **Alternative:** have the library return the pinned joints and let the tool keep
  the literal "pin or the selection" behaviour.


## D18. Quirks kept in the moved builders (phase 4b)

- **Kept for identical output:**
  - the forced `print_result`/`log_result` calls;
  - the `print(increment)` lines in the spline builder;
  - an unused `blendColors` node in the twist builder.
- **Why:** removing the node would change creation order, and so the default
  node names.
- **Alternative:** remove these when a behaviour change is acceptable (for example
  at 4.0).


## D19. Remaining `aniseed_toolkit.run("...")` calls in components (phase 5)

- **Chosen:** components and hosts which still call tools by name keep doing so,
  for example `spline_spine` calling `run("Create Spline Setup")`.
  - `run()` is the public tool API, and calling through it adds an undo chunk.
  - `twister.py` was switched to `rigging.twist.create_twist_setup`, because it
    was edited in 4b anyway.
- **Alternative:** switch every component to the direct library calls for clarity.
  The output would be identical apart from undo chunking.


## D20. Where maya.cmds stays in the library (phase 6)

- **Chosen:**
  - **Use mref** for:
    - nodes a function creates and owns (temporary nodes, new rig nodes);
    - attribute, constraint and matrix work where the result is provably
      identical.
  - **Keep cmds** where the function returns or reuses names exactly as Maya
    reports them:
    - `cmds.rename` and `cmds.listConnections` can return partial paths such as
      `|foo`, which mref's `name()` does not reproduce;
    - `controller`, `ls(long=True)`, `selection.first_selected` and
      `currentUnit`;
    - component strings such as `curve.cv[*]` and vertex lists, which mref does
      not wrap.
  - **Keep OpenMaya** for:
    - `core.api`, whose whole purpose is MObject/MDagPath;
    - per-CV maths in `scene.shapes` and `scene.surfaces`;
    - the skin weight api in `scene.skin`.
  - Every module says why in a comment or module docstring.
- **Precision rule found:** replacing a flag-less `cmds.xform(query/matrix)` with
  mref `get_matrix`/`get_position`/`set_matrix` adds `objectSpace=True`. That is not
  bit-identical, and changed `aimMatrix` values in the last digit. Use
  `node.xform(...)` with the original flags instead.
- **Evaluation rule found:** `Attribute.set` queries the attribute type first,
  which evaluates the attribute. In `rig.guide` this changed later tween blend
  defaults (0.37 became 0.27), so that loop uses the `mref.setAttr` passthrough.
- **Alternatives:**
  - Convert the name-returning calls too and accept full or short names
    differing from today. That is a return value change, deferred to 4.0 at the
    earliest.
  - Extend mref with component support and a "name as Maya reports it" accessor.


## D21. Errors for bad node names (phase 6)

- **Chosen:** wherever a caller-supplied name is now resolved through mref,
  `aniseed_toolkit.core._nodes.resolve(node, error=ValueError)` raises the error
  Maya used to raise:
  - "No object matches name: x" when nothing matches;
  - "More than one object matches name: x" when several nodes match.
  - mref.get on its own would return the string (giving a later AttributeError)
    or silently pick the first match.
- **Details:**
  - The error type follows the cmds command that used to fail first: RuntimeError
    where that was `nodeType` (visibility, sets, and shapes.apply_color, rotate,
    scale and shape_to_dict).
  - `scene.shapes` has its own `_get_node` with the same rule.
  - `attributes.lock_and_hide` does not resolve at all. cmds.setAttr on an
    ambiguous name edits every match, and that behaviour is kept.
  - Messages are cmds' wording, not always its exact text (nodeType's message
    differs).
- **Alternatives:**
  - Let mref's own errors through (simpler, but a behaviour change).
  - Make mref.get itself strict.


## D22. Shims stay until 4.0 (phase 7 not done)

**Superseded by D24:** phase 7 was done in 4.0.0 at the user's request.

- **Chosen:** phase 7 (removing the old module paths) is deliberately not done.
  - The plan keeps the shims for at least one minor release.
  - All code in this repo now uses the new paths. A strict build that turns the
    shims' DeprecationWarnings into errors passes for every test scene.
- **How to do it later:**
  - delete `aniseed_toolkit/lib/*` shims, `_legacy`, and the top-level
    `__getattr__` map;
  - bump to 4.0.
- **Alternative:** remove them now if no external scripts use the old paths.


## D23. No mixins other than MirrorMixin (user request, after phase 6)

- **Chosen:** JointChainMixin, InsertControlMixin and SingularControlMixin were
  removed. They were introduced by the component cleanup, not the original code.
  - Shared logic became plain toolkit helpers that take values, not components:
    - `scene.joints.get_chain(root, tip, extra_joints)`;
    - `scene.joints.remove_chain(root, chain_joints)`;
    - `rig.control.create_with_offset(...)`, which returns
      `(control, offset_control_or_None)`.
  - Each component now has its own `all_joints`, `all_guides` (Leg and Tri Leg
    only), `on_removed_from_stack`, `user_func_create_mirror`, widget,
    `is_valid` and `suggested_label` methods. These call the helpers above.
  - The option, input and output declarations are copied into each component
    rather than shared, as the user chose, so every component file lists all its
    own attributes.
  - `aniseed_toolkit.lib.control_mixins` and the `JointChainMixin` entry of the
    `lib.component` shim were deleted, not deprecated. They never existed before
    this refactor, and nothing had been pushed.
  - Arm no longer has an `all_guides` method. The mixin's version always returned
    `[]`, nothing calls it, and the original Arm did not have one.
- **Alternative:** a toolkit function that declares the shared attributes on a
  component passed in (e.g. `declare_singular_attributes(component, ...)`). That
  avoids duplicated declarations but is a mixin in all but name.


## D24. Shims removed in 4.0.0 (phase 7, user request)

- **Chosen:** the user confirmed that aniseed and its components are the only
  users of aniseed_toolkit, so the compatibility layer was deleted on `main`:
  - the `aniseed_toolkit/lib` package (all module shims and `lib/rigging`);
  - the `aniseed_toolkit/app` package (old location of the toolkit UI, now `ui.app`);
  - the `aniseed_toolkit/_legacy` package (dead code only reachable through the shims);
  - the top-level `_OLD_MODULES` map and the `app` / `lib` lazy names in
    `aniseed_toolkit/__init__.py`;
  - the moved-module map and legacy `__getattr__` in `aniseed_toolkit/rigging`.
- No code in the repo used those paths, so no component changed. The only other
  edit was the Spring "Control Shape" description, which named the old path.
- aniseed and aniseed_toolkit are both 4.0.0, and the README describes the change.
- **Alternative:** keep the shims for external scripts. Not needed, as there are none.