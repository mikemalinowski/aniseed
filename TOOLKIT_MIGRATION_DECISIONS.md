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