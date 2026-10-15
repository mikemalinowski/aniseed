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