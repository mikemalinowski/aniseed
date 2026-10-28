# aniseed_utilities

This is the base aniseed package for Maya. It holds:

* the utility library, used by components, tools and riggers' own scripts:
  * `core/` : naming, maths, attributes, selection and directions
  * `scene/` : transforms, joints, constraints, shapes, skin, surfaces and node maths
  * `rig/` : controls, guides, tagging, pinning, spaces and the pose mixer
  * `mixins/` : optional component capabilities, such as `MirrorMixin`
  * `ui/` : dialogs (imports Qt, so import `aniseed_utilities.ui.dialogs` explicitly)
  * `utils.py` (undo chunks) and `resources.py` (the `_res` folder, including
    the control shape library in `_res/shapes`)
* `components/` : general purpose components (utilities, the global control
  root, space switching, control insertion, the singulars...)
* `hosts/` : the Maya host, which builds the Aniseed menu, docks the app and
  the toolkit windows, and runs each toolkit tool as one undo step. As it
  provides a host, this package is always on.

Rig building blocks (ik / ikfk setups, soft ik, foot roll, twist, spline and
ribbon setups...) are not part of this package. They live in
`aniseed_standard.rigging`, alongside the components which use them.

## Using the library

Code outside the library (components, tools, the host, other packages and
your own scripts) imports it as `au`:

```python
import aniseed_utilities as au

distance = au.core.maths.distance_between(node_a, node_b)
control = au.rig.control.create(description="arm", location="l", parent=org, shape="core_circle", config=config)


class MyComponent(aniseed.RigComponent, au.mixins.MirrorMixin):
    ...
```

The library is layered, and each layer only uses the layers before it:
`core` < `scene` < `rig` < `mixins` < `ui`. Modules within the library import
each other relatively (`from ..scene import shapes as _shapes`).

**Nothing in this package may import any other aniseed package.** Other
packages build on this one (`aniseed_standard` requires it), never the other
way around.

## Aniseed packages

An aniseed package is any folder containing an `aniseed_package.json` file.
The folder name is the package name, and must be a valid python module name.
Aniseed looks for these optional folders within it:

| Folder        | Use                                                   |
|---------------|-------------------------------------------------------|
| `components/` | Added to the component factory                        |
| `hosts/`      | Added to the host factory                             |
| `mixins/`     | Importable as `<package_name>.mixins`                 |
| `widgets/`    | Importable as `<package_name>.widgets`                |
| `tools/`      | Searched by the toolkits for `aniseed.toolkits.Tool` subclasses |
| `_res/icons/` | Icons for the package's tools and categories, named `<identifier>.png` / `<category>.png` |

Any other python package folder is importable too, as
`<package_name>.<folder>`. This is how a package carries library code of its
own, such as `aniseed_utilities.scene` or `aniseed_standard.rigging`.

Tools in a package's `tools/` folder show in the toolkit their `toolkit`
attribute names (such as "Rigging"), and can be run from code with
`aniseed.toolkits.run("<tool identifier>", options={...})`, including in
headless sessions. They are found by subclassing `aniseed.toolkits.Tool` -
there is nothing to register.

A package is itself a toolkit if its `aniseed_package.json` has a `"toolkit"`
entry (see `aniseed_rigging_toolkit`), which adds it to the Aniseed menu.

Packages are found alongside the aniseed module, and in any of the paths
given in the `ANISEED_PACKAGE_PATHS` environment variable (split by `;` or
`,`). Each of those paths can be a package, or a folder of packages.

The `aniseed_package.json` file can be empty (`{}`), or contain:

```json
{
    "version": "1.0.0",
    "description": "What the package is for",
    "hosts": ["maya"],
    "requires": ["aniseed_utilities"],
    "enabled_by_default": true
}
```

* `hosts` : the hosts this package is used in. If empty it is used in all of them.
* `requires` : other packages this package needs. Aniseed warns if one is missing.
* `enabled_by_default` : whether the package is on until the user chooses
  otherwise. Defaults to `true`. `aniseed_dev_examples` sets it to `false`.

## Turning packages on and off

In the aniseed app, **Edit > Packages...** lists every package for the current
host, with a check box to turn each one on or off. Choices are saved for the
user (with scribble, as `aniseed_packages.json`), and take effect straight
away. **Reset to Defaults** forgets them.

* A package which is off contributes no components (or toolkit tools). Rigs
  which already use its components keep their data, but those components load
  as placeholders and cannot be built until the package is on again.
* Packages which provide a host (have a `hosts/` folder) are always on.
* Turning a package on also turns on the packages it `requires`, and a package
  whose requirement is off is treated as off too.

From code, `aniseed.packages.set_enabled(name, True)` does the same. Pass
`persist=False` to turn a package on (or off) for the current session only,
without changing the user's saved choice, which suits scripts and tests.

Component and tool identifiers must be unique across all packages. A package
should not use the identifier of a component or tool elsewhere to replace it.
