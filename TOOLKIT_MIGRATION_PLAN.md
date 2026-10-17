# aniseed_toolkit migration plan (A + C)

Target: a layered library (A) whose functions are the API, with user tools
registered from functions by a decorator (C). Component-support code moves into
aniseed. Every step is incremental, behind compatibility shims, and verified.

Status: all phases done. Phases 0-6 were done on branch `toolkit-restructure`
and merged into `main`. Phase 7 (removing the shims) was done on `main` for
4.0.0, see decision D24.
Commits: 8f7fb35 (1a), 8e145f1..a67d6ec (individual fixes), 0200c51, 7a03997 (2),
b0b9468 (3), 66d6b4d (4a), d7466c4 (4b), 87a2c73 (5), 87b7fed (6).
Decisions taken while implementing are in TOOLKIT_MIGRATION_DECISIONS.md.


## 1. Rules the new structure enforces

1. Layers, lowest first: core, scene, rig, rigging, tools, ui. A module may only
   import from its own layer or the layers below it.
2. Library layers (core, scene, rig, rigging) never call `run()`, never read or
   change the selection, and never import Qt or qtility. Anything that prompts the
   user or works on the selection belongs in tools or ui.
3. Inside the package, imports are relative and happen at module level
   (`from ..scene import joints`). No module does `import aniseed_toolkit` to reach
   a sibling.
4. The toolkit never imports aniseed at runtime. The rig configuration is used by
   duck typing (generate_name, organisational, control, ...); type hints import it
   under `typing.TYPE_CHECKING` only.
5. Every package `__init__` lists its public API explicitly (no star imports).
6. API conventions:
   - accept str or mref items for nodes;
   - functions that create nodes return the same type as today until phase 6
     (see section 7);
   - mref over cmds inside the library, except where documented.


## 2. Target layout

    aniseed_toolkit
      __init__              explicit public API + compatibility aliases (PEP 562 __getattr__)
      registry              Tool base class, ToolBox, @tool decorator, run(), register()
      resources             (unchanged)
      core
        units               cm conversions
        naming              unique name helpers
        maths               vector / matrix / distance helpers, upvector calculation
        attributes          separator, lock_and_hide
        selection           first_selected and other selection queries (used by tools/ui only)
        direction           Direction class
        api                 OpenMaya handle helpers (deprecated, see section 3)
      scene
        transforms          create, matching, relative matrices, snapping, aim, scaling, matrix drive
        joints              everything in today's joints + create under selection
        constraints         parent_and_scale, blend_weights, remove_all
        node_math           floatMath style helpers
        shapes              curve shape create / edit / colour / save / load
        skin                skin data and weight utilities
        surfaces, sets, visibility, hierarchy_io, mirror
      rig
        control             Control, create, get, zero transform, offset controls, curve queries
        guide               guides and guide links
        space               get_root_control
        tagging, pinning
        controls            all_controls, opposing_controls, controls_by_location, get_rig_node
        pose_mixer          the TransformMixer pose system used by face and transform_mixer
      rigging
        ik, ikfk, foot, soft_ik, two_bone_ikfk, blend_chain, rotator, facial
        twist, spline, ribbon, aim_hierarchy, bone_alignment   (moved out of tools)
      tools                 user facing actions (decorated functions + legacy Tool classes)
        controls, creation, interaction, joints, shapes, skinning, transforms, rigging, docs
      ui                    toolkit app, widgets, dialogs (qtility / Qt only here)


## 3. Module mapping (current -> new)

"shim" means the old import path keeps working and logs a deprecation warning
(section 5).

| Current | New home | Notes |
|---|---|---|
| units | core.units | |
| naming.unique | core.naming.unique | |
| rigging.two_bone_ikfk.unique_name | core.naming.unique(start=2) | keep the counter-from-2 behaviour (it decides node names) |
| attributes | core.attributes | |
| direction.Direction | core.direction | fix set_direction bug (phase 1) |
| direction.get_chain_facing_direction, get_upvector_direction | scene.joints | |
| mutils.first_selected | core.selection | |
| mutils.get_name / get_mobject / get_dagpath | core.api, deprecated | mref replaces these; remove the 5 component uses of run("MObject Name") / run("Get MObject") |
| transformation: distance_between, factor_between, direction_between, interpolate_vector, calculate_upvector_position, calculate_four_point_spline_positions | core.maths | |
| transformation.timed_function_call | core.maths (or drop) | debug decorator |
| transformation: snap_position, position_between, get_relative_matrix, apply_relative_matrix, aim_at, scale_translation, scale_translation_of_hierarchy | scene.transforms | |
| transformation.TransformMixer | rig.pose_mixer | |
| transformation.TransformMixerUi | delete | empty stub, and the reason transformation imports PySide6 |
| transforms.create, create_locator_at_center | scene.transforms | create_locator_at_center returns a list despite its str annotation, and ignores its argument |
| matrix_drive | scene.transforms.drive_from_local_matrix | |
| stack_joints.create_from_selection | scene.joints.create_under(parent) + tools-side selection | the library takes the parent; the caller resolves the selection |
| joints | scene.joints | fix replicate_chain(replacements=...) (phase 1) |
| constraints | scene.constraints | |
| containts.remove_all | scene.constraints.remove_all | the typo module becomes a shim |
| rigging.node_math | scene.node_math | it creates nodes, so it belongs in scene |
| shapes | scene.shapes | rename shapes.global_mirror to mirror_by_name (it clashes with mirror.global_mirror) |
| skin | scene.skin | fix load() not returning the skinCluster |
| surfaces, sets, visibility | scene.* | fix visibility.hide/show nodeType test |
| io | scene.hierarchy_io (+ ui dialogs) | the qtility prompts move to ui |
| mirror | scene.mirror (+ ui prompt) | global_mirror's interactive prompt moves to ui; the library version needs explicit args |
| control | rig.control | |
| offset_controls | rig.control.add_offset_control | |
| control_queries | rig.control (curve_controls, has_curve_shapes) | |
| guide | rig.guide | delete create_multi (broken) and create_ik_guide (unused) |
| space.get_root_control | rig.space | |
| tagging | rig.tagging | fix find_all ignoring its tag |
| pinning | rig.pinning | fix pin() shape assignment (selection bug) |
| rig: all_controls, get_rig_node, opposing_controls, controls_by_location | rig.controls | |
| rig.get | aniseed (aniseed.get_rig exists already) | it returns an aniseed.Rig, so it belongs to aniseed |
| rigging.ik, ikfk, foot, blend_chain, rotator, two_bone_ikfk | rigging.* | |
| rigging.softik + multi_bone_softik | rigging.soft_ik | two functions in one module, sharing node_math |
| rigging.transform_mixer.TransformMixer | delete | unused, and it shadows the real one by name |
| facial_controls | rigging.facial | no aniseed dependency, so it stays in the toolkit |
| tools/maya/rigging/twist (TwistSetup) | rigging.twist | a builder that currently lives inside a tool; Twister reaches it with run("Create Twist Setup") |
| tools/maya/rigging/spline, ribbon2 | rigging.spline, rigging.ribbon | same: builders living in tools |
| tools/maya/rigging/guide_follow, ik | rigging.aim_hierarchy, rigging.bone_alignment | same |
| app.widgets | ui.app | |
| utils.UndoChunk | registry (used by run) | |

Moves into aniseed (component plumbing, not general rigging):

| Current | New home in aniseed |
|---|---|
| component.JointChainMixin | removed (D23): each limb has its own methods, using scene.joints.get_chain / remove_chain |
| control_mixins.InsertControlMixin, SingularControlMixin | removed (D23): declarations live in each component, using rig.control.create / create_with_offset |
| component.add_twister | aniseed.builders.add_twister |
| space.add_space_switch, setup_fk_worldspace_switches, setup_fk_transform_worldspace_switches | aniseed.builders (they create Space Switch components) |
| component.mirror | aniseed.builders.mirror_component |
| component.request_count, option_files | aniseed.dialogs |
| component_outputs | aniseed.component_outputs (or methods on RigComponent) |

aniseed.mixins already exists (MirrorMixin). aniseed.builders and aniseed.dialogs
are new and small.


## 4. Tool registration (C)

Today there are 133 tools: 63 are one-line wrappers around a lib function, 68 have
their own logic. The lib calls tools by name 20 times, and components 7 times.

New registry:

    @tool("Get Joints Between", category="Joints")
    def get_between(start: str, end: str) -> list[str]: ...

- The decorator records the identifier, category, classification, icon, version
  and user_facing on the function, then returns the function unchanged. Calling it
  directly is a normal Python call.
- ToolBox discovers two kinds of tool:
  - Tool subclasses (unchanged, so external ANISEED_TOOLKIT_PATHS plugins keep
    working);
  - decorated functions in the toolkit's modules.
- A small adapter makes a decorated function look like a Tool to the existing UI:
  run() calls the function inside the undo chunk, signature() reads the function's
  signature, and documentation() reads its docstring.
- Identifiers are unchanged, so shelves, scripts and run("...") calls keep working.

Conversions:

- **The 63 thin wrappers:** delete the wrapper classes and decorate the library
  function with the same identifier.
  - Before converting, snapshot each wrapper's run() signature and diff it with the
    library function's. Where the parameter names or defaults differ (the UI builds
    its form from them), keep a small adapter function in tools.
  - Wrappers marked code-only (user_facing = False) are registered as code-only. They
    exist purely as a string API, so they are candidates for deprecation (log a
    warning when called via run).
- **The 68 tools with logic:** become functions in tools.* that resolve the
  selection, prompt if needed, then call the library. The rigging builders hidden
  in tools (twist, spline, ribbon, aim hierarchy, bone alignment) move to rigging
  first, leaving thin tools behind.
- **Calls that bypass the library:**
  - Every lib -> run() call is replaced by a direct call.
  - The selection-acting tools (Apply Shape, Scale/Rotate/Offset Shapes, Apply Shape
    Color) get library equivalents that take the node, and the tools pass the
    selection in.
  - This removes control.create's hidden dependence on the selection.
- **Other fixes:**
  - Remove the second ToolBox() created in the package init; everything uses the
    singleton.
  - Remove the debug prints in register().


## 5. Compatibility

Every existing import path keeps working through at least one release.

- The top-level package defines `__getattr__` (PEP 562):
  `aniseed_toolkit.transformation`, `.mutils`, `.containts`, `.joints` etc. resolve
  to the new modules and log a single DeprecationWarning per name. A small table
  maps old name -> new module (or for split modules, an alias module that
  re-exports exactly the old public names).
- lib becomes a package of shims: each old module file re-exports its old public
  names from their new homes. This keeps `from aniseed_toolkit.lib import joints`
  style imports working.
- `aniseed_toolkit.rigging.*` keeps its current names; the rigging layer keeps that
  name.
- Names moving into aniseed (mixins, builders) are re-exported lazily from the
  toolkit shims. The import happens inside `__getattr__`, so the toolkit still never
  imports aniseed at load time.
- Tool identifiers never change.
- Shims are removed in the next major version (4.0), after the components and the
  owner's own scripts have moved over.


## 6. Phases

Each phase ends with the verification in section 8. Commit after every phase.

**Phase 0: safety net (small)**
- Commit the current state.
- Keep the rig regression harness from the component refactor: 12 scenes, the
  fixture generation checks and the extra fixtures.
- Add two snapshots that must not change:
  - **Tool registry:** every identifier, its version, user_facing flag, category
    and run signature.
  - **Public API:** every name reachable as aniseed_toolkit.<module>.<name> today.
    Each must still resolve after every phase.

**Phase 1: cleanups in place, no moves (small)**
- Delete the dead code: guide.create_multi, guide.create_ik_guide,
  rigging.transform_mixer, transformation.TransformMixerUi, the unused locals and
  debug prints.
- Replace the 20 lib -> run() calls with direct library calls.
  - control.create switches from "Apply Shape" / "Scale Shapes" (selection based)
    to shapes.load_shape / shapes.scale on the control.
  - This is output-identical today because the selection at that point is the
    control. The harness proves it.
- Remove the second ToolBox and register()'s prints.
- Make PySide6 a lazy import (removing TransformMixerUi removes it entirely).
- **Decision needed:** fix the broken functions? These are tagging.find_all,
  visibility.hide/show, Direction.set_direction, replicate_chain with replacements,
  skin.load's return value and pinning.pin.
  - Each currently returns wrong results or raises, and no component build path
    uses them, but tools do.
  - Recommendation: fix them here as one commit per fix, so each can be reverted
    on its own.

**Phase 2: registry and decorator (medium)**
- Add the registry module, the @tool decorator, function-tool discovery and the
  Tool adapter.
- Convert the 63 thin wrappers, using the signature diff from phase 0.
- The tool registry snapshot must be identical, apart from the reported adapter
  cases.

**Phase 3: new layout, library modules (large, but mechanical)**
- Create core, scene, rig and rigging per section 3. Move the code with history
  preserved (git mv first, then split the multi-destination modules).
- Convert intra-package imports to relative, layer-respecting imports.
- Add a check that fails on upward or circular imports. It is a short script that
  parses imports and checks the layer order; run it in the verification step.
- Add the lib shims and the PEP 562 aliases.
- Move the builders hidden in tools into rigging.

**Phase 4: tools and ui (medium)**
- Move the tools with logic to tools.* as functions (or keep them as Tool classes
  where a class is genuinely needed).
- Move the qtility / Qt code (dialogs, mirror prompt, hierarchy io dialogs, app) to
  ui.

**Phase 5: component support into aniseed (small)**
- Create aniseed.builders and aniseed.dialogs; move the mixins into aniseed.mixins.
- Update the components to import from aniseed and from the new toolkit paths.
  This is mechanical and can be done with a scripted rewrite plus review.
- After this, no component uses a shim. The harness must show zero deprecation
  warnings during a build.

**Phase 6: conventions (ongoing, per module)**
- Move the library from cmds to mref, module by module (424 cmds calls today).
- Settle return types:
  - **Current behaviour:** most functions return short-name strings, rigging
    builders return mref items or builder objects, and create_rotator returns a
    str despite its annotation.
  - **Proposal:** keep returning str from existing functions (changing it would
    break every caller), and make new functions return mref items. Alternatively,
    add return_type parameters only where callers need them. Decide per module;
    don't do a global flip.
- Docstrings for the public API (they become the tool documentation automatically,
  through the decorator).

**Phase 7: remove shims (4.0)**
- Delete the lib shims and aliases once nothing logs deprecation warnings.


## 7. Behaviour that must be preserved (known output-affecting details)

- The naming schemes: naming.unique counts from 1, and two_bone_ikfk's helper counts
  from 2. Both decide node names in existing rigs.
- The order in which unnamed nodes (utility nodes, constraints) are created. Moving
  code must not reorder node creation.
- Functions keep their current return types until phase 6 deliberately changes them.
- control.create without match_to currently matches the selection. After phase 1 it
  is explicit: no match_to means each node is re-matched to its own world transform
  (in practice the world origin, as the nodes are created there and parented
  absolutely; see decision D3). Today this is equivalent
  only because the selection is the new node. The harness confirms this for every
  component; external callers relying on the old behaviour are unlikely, but the
  change goes in the release notes.
- The soft IK node graphs, including the nodes nothing reads (they keep later node
  names stable).


## 8. Verification for every phase

1. Rig harness:
   - 12 build scenes compared IDENTICAL against the baseline;
   - fixture generation compared IDENTICAL;
   - the extra fixtures (soft IK two bone, limb variants, blendshape face);
   - no component build failures.
2. Tool registry snapshot identical (identifiers, versions, flags, categories,
   signatures).
3. Public API snapshot: every old name still resolves.
4. The layer / import check passes (from phase 3).
5. Import smoke test in a fresh mayapy: import aniseed_toolkit and every module,
   with no Qt available for the library layers. That proves rule 2.
6. Manual GUI pass in Maya at the end of phases 2, 4 and 5: the toolkit app lists the
   same tools, a sample of tools run, and the component UIs open.


## 9. Risks

- **Owner scripts and shelves** using old paths or tool names: covered by the shims
  and the unchanged identifiers. Deprecation warnings show what needs updating.
- **External plugins** subclassing Tool via ANISEED_TOOLKIT_PATHS: the Tool class is
  unchanged.
- **Tools whose run() signature differs from the library function's:** the UI form
  would change. Handled by the phase 0 snapshot and adapters.
- **Hidden selection dependencies surfacing** when lib -> run() calls are removed:
  the harness covers component builds. Tools that relied on them are checked in the
  GUI pass.
- **Large diffs:** phase 3 is mostly moves. Keep moves and edits in separate commits
  so history stays readable.


## 10. Open decisions

1. Fix the six broken library functions in phase 1 (recommended), or keep them
   as-is and only document them?
2. Names for the new aniseed modules: aniseed.builders and aniseed.dialogs are
   proposals.
3. Return type policy (phase 6): keep str for existing functions and use mref for
   new ones (recommended), or per-function parameters?
4. Deprecation window: remove the shims at 4.0, or keep them indefinitely?
5. Code-only thin tools (string API only, for example "MObject Name", "Get Joints
   Between"): keep them registered permanently, or deprecate them via run()?
