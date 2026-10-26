# aniseed_maya_standard

This is an aniseed package holding the standard Maya content for aniseed:

* `components/` : the Maya rigging components (limbs, augments, utilities...)
* `mixins/` : the mixins those components use, such as `MirrorMixin`
* `hosts/` : the Maya host, which builds the Aniseed menu, docks the app and
  the toolkit windows, and runs each toolkit tool as one undo step
* `tools/` : toolkit tools, such as the face skeleton load/save tools (shown in
  the Rigging Toolkit)

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

Tools in a package's `tools/` folder show in the toolkit their `toolkit`
attribute names (such as "Rigging"), and can be run from code with
`aniseed.toolkits.run("<tool identifier>", options={...})`, including in
headless sessions. They are found by subclassing `aniseed.toolkits.Tool` -
there is nothing to register.

A package is itself a toolkit if its `aniseed_package.json` has a `"toolkit"`
entry (see `aniseed_maya_rigging_toolkit`), which adds it to the Aniseed menu.

Packages are found alongside the aniseed module, and in any of the paths
given in the `ANISEED_PACKAGE_PATHS` environment variable (split by `;` or
`,`). Each of those paths can be a package, or a folder of packages.

The `aniseed_package.json` file can be empty (`{}`), or contain:

```json
{
    "version": "1.0.0",
    "description": "What the package is for",
    "hosts": ["maya"],
    "requires": ["aniseed_maya_standard"],
    "enabled_by_default": true
}
```

* `hosts` : the hosts this package is used in. If empty it is used in all of them.
* `requires` : other packages this package needs. Aniseed warns if one is missing.
* `enabled_by_default` : whether the package is on until the user chooses
  otherwise. Defaults to `true`. `aniseed_maya_dev_examples` sets it to `false`.

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
