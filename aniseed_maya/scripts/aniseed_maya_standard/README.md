# aniseed_maya_standard

This is an aniseed package holding the standard Maya content for aniseed:

* `components/` : the Maya rigging components (limbs, augments, utilities...)
* `mixins/` : the mixins those components use, such as `MirrorMixin`
* `hosts/` : the Maya host, which builds the Aniseed menu and docks the app
* `tools/` : aniseed_toolkit tools, such as the face skeleton load/save tools

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
| `tools/`      | Searched by aniseed_toolkit for `aniseed_toolkit.Tool` subclasses |

Tools in a package's `tools/` folder show in the toolkit app and can be run with
`aniseed_toolkit.run("<tool identifier>")`, including in headless builds. They are
found by subclassing `aniseed_toolkit.Tool` - there is no need to call
`aniseed_toolkit.register`.

Packages are found alongside the aniseed module, and in any of the paths
given in the `ANISEED_PACKAGE_PATHS` environment variable (split by `;` or
`,`). Each of those paths can be a package, or a folder of packages.

The `aniseed_package.json` file can be empty (`{}`), or contain:

```json
{
    "version": "1.0.0",
    "description": "What the package is for",
    "hosts": ["maya"],
    "requires": ["aniseed_maya_standard"]
}
```

* `hosts` : the hosts this package is used in. If empty it is used in all of them.
* `requires` : other packages this package needs. Aniseed warns if one is missing.

Component and tool identifiers must be unique across all packages. A package
should not use the identifier of a component or tool elsewhere to replace it.
