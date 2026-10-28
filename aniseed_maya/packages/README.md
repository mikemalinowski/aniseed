# Aniseed Packages

This folder holds the aniseed packages that ship with aniseed for Maya.

## What is a package?

A package is a bundle of things you use while rigging, kept together in one
folder. A package can give you:

* **Components**: the building blocks you add to a rig in the aniseed
  window, such as limbs, spines and utility steps.
* **Tools**: the buttons in the Rigging and Animation toolkits, such as
  shape, joint and skinning tools.
* **Toolkits**: the toolkit windows themselves, opened from the Aniseed menu.
* **Shapes, icons and other resources** that those components and tools use.

Each package one adds a set of features, and you can turn it on or off 
without touching the others.

### The packages in this folder

| Package                     | What it gives you                                                                                            | On by default |
|-----------------------------|--------------------------------------------------------------------------------------------------------------|---------------|
| `aniseed_utilities`         | General utility components, such as Root, Space Switch and Insert Control. Every other package relies on it. | Always on |
| `aniseed_standard`          | The standard limbs and mechanisms, such as arms, legs, spines and heads.                                     | Yes |
| `aniseed_cartoon`           | Cartoon style components.                                                                                    | Yes |
| `aniseed_rigging_toolkit`   | The Rigging Toolkit window and its tools.                                                                    | Yes |
| `aniseed_animation_toolkit` | The Animation Toolkit window and its tools.                                                                  | Yes |
| `aniseed_dev_examples`      | Documented example components, for people learning to write their own.                                       | No |

### Turning packages on and off

1. Open the aniseed window.
2. Go to **Edit > Packages...**
3. Tick a package to turn it on, or untick it to turn it off.

The change happens straight away, with no need to restart Maya, and aniseed
remembers your choice the next time you open Maya. To put every package back
to how it started, press **Reset to Defaults**.

A few things worth knowing:

* **Some packages need other packages.** The *Requires* column shows which
  ones. If a package needs one that is turned off, its *Status* says
  something like `Off: needs aniseed_standard`. Turning a package on also
  turns on the packages it needs.
* **`aniseed_utilities` cannot be turned off.** It connects aniseed to Maya,
  so its row is greyed out.
* **Turning a package off never damages your rigs.** Its components disappear
  from the list of components you can add. A rig that already uses them keeps
  all of its settings, but those components show as missing and cannot be
  built. Turn the package back on and they work again.
* **Double click a package** to open its folder.

If a rig suddenly shows missing components, check this window first. The
package those components come from is probably turned off.

---

# Technical Documentation

The rest of this page is for people writing or maintaining packages.

## How packages are found

This folder is on the `ANISEED_PACKAGE_PATHS` environment variable, which the
`aniseed.mod` file sets up (`ANISEED_PACKAGE_PATHS+:=packages`). The mod file
also adds this folder to `PYTHONPATH`, so the packages here can be imported
by name.

Aniseed searches for packages (see `aniseed/packages.py`) in this order:

1. Each path in `ANISEED_PACKAGE_PATHS`, split on `;` or `,`.
2. The folder that contains the `aniseed` module itself.

Each of those paths can either be a package itself, or a folder of packages.
Within a folder, packages are found in alphabetical order.

Any folder that contains an `aniseed_package.json` file is a package. The
folder name is the package name, and it must be a valid python module name,
as the package is imported by it. A folder whose name is not a valid name is
skipped, with a warning.

Only one package of a given name can exist. If two search paths both provide
`my_package`, the one found first wins and the other is skipped, with a
warning. This lets a studio put an override of a package earlier in
`ANISEED_PACKAGE_PATHS`.

When a package is found, the folder that contains it is added to `sys.path`.
This means it is imported by its name (`import aniseed_utilities`), and its
own modules (such as `hosts/maya.py`) cannot shadow real modules.

Packages are found once and then cached for the session.
`aniseed.packages.discover(refresh=True)` searches again.

## The structure of a package

```
my_package/
    aniseed_package.json    <- required: marks the folder as a package
    __init__.py             <- optional: makes the package importable as a python package
    README.md
    components/             <- rig components, added to the component library
    tools/                  <- toolkit tools (aniseed.toolkits.Tool subclasses)
    hosts/                  <- embedded hosts, such as hosts/maya.py
    mixins/                 <- importable as my_package.mixins
    widgets/                <- importable as my_package.widgets
    _res/
        icons/              <- icons for tools and categories: <identifier>.png / <category>.png
    my_library/             <- any other python package, importable as my_package.my_library
```

Every folder is optional. Aniseed uses each one as follows:

| Folder        | Use                                                                                                    |
|---------------|--------------------------------------------------------------------------------------------------------|
| `components/` | Added to the component factory paths. Every `RigComponent` subclass in it shows in the component list. |
| `tools/`      | Searched by the toolkits for `aniseed.toolkits.Tool` subclasses. There is nothing to register.        |
| `hosts/`      | Added to the embedded host factory paths. A package with this folder can never be turned off.         |
| `mixins/`     | Importable as `<package_name>.mixins`, for components to inherit from.                                |
| `widgets/`    | Importable as `<package_name>.widgets`.                                                               |
| `_res/icons/` | Icons for the package's tools and tool categories.                                                    |

### Library code inside a package

Any other python package folder inside a package can be imported as
`<package_name>.<folder>`. This is how a package carries shared library code
alongside its components. For example:

* `aniseed_utilities` carries `core`, `scene`, `rig` and `ui`, which every
  other package uses.
* `aniseed_standard` carries `rigging`, the building blocks its limbs use.

Library files within a package may use relative imports of each other.
Components and tools should import libraries absolutely, by package name:

```python
import aniseed_utilities as au
from aniseed_standard import rigging

control = au.rig.control.create(...)
```

### Tools and toolkits

A tool in any package's `tools/` folder appears in the toolkit that its
`toolkit` class attribute names, such as `"Rigging"`. So any package can add
tools to the Rigging Toolkit without the toolkit knowing about it.

A package *is* a toolkit when its `aniseed_package.json` has a `"toolkit"`
entry. That package provides the toolkit window, so it must have a `launch()`
function and is added to the Aniseed menu. Only one package should declare a
given toolkit. If more than one does, aniseed warns and uses the first.
Packages that only add tools to a toolkit should not have a `"toolkit"` entry.

## The aniseed_package.json file

The file can be empty (`{}`), but usually looks like this:

```json
{
    "version": "1.0.0",
    "description": "What the package is for",
    "hosts": ["maya"],
    "requires": ["aniseed_utilities"],
    "enabled_by_default": true
}
```

| Key                  | Type            | Default | Meaning                                                                                                    |
|----------------------|-----------------|---------|------------------------------------------------------------------------------------------------------------|
| `version`            | string          | `""`    | The package's version. Shown in the Packages window.                                                       |
| `description`        | string          | `""`    | A short description. Shown in the Packages window.                                                         |
| `hosts`              | list of strings | `[]`    | The host applications this package is written for, such as `["maya"]`. If empty, it is used in every host. |
| `requires`           | list of strings | `[]`    | The names of the packages this package depends on. See below.                                              |
| `enabled_by_default` | bool            | `true`  | Whether the package is on until the user chooses otherwise.                                                |
| `toolkit`            | string          | none    | The name of the toolkit this package provides, such as `"Rigging"`. Only for toolkit packages.             |

If the file is not valid JSON, aniseed warns and treats it as empty.

Packages whose `hosts` do not include the current host are ignored entirely.
They do not show in the Packages window, and their components and tools are
not loaded.

## Requirements and enabling

### Declaring a requirement

If any code in your package imports another package, list that package in
`requires`:

```json
"requires": ["aniseed_standard", "aniseed_utilities"]
```

List every package you import directly, even if it is also required by one
of your other requirements. In the example above, `aniseed_standard` already
requires `aniseed_utilities`, but `aniseed_cartoon` lists it too because its
components import it.

Requirements are only between packages. They should never form a loop. The
dependency direction in this folder is:

```
aniseed_utilities  <-  aniseed_standard  <-  aniseed_cartoon
        ^
        +---- aniseed_rigging_toolkit, aniseed_animation_toolkit, aniseed_dev_examples
```

Nothing in `aniseed_utilities` may import any other package.

### How a package's state is decided

Whether a package is used is decided in two steps.

**1. Is it chosen?** A package is chosen if:

* it has a `hosts/` folder, in which case it is always chosen, or
* the user has turned it on (or off) in the Packages window, in which case
  that choice is used, or
* failing that, its `enabled_by_default` value says so.

**2. Is it enabled?** A package is enabled (active) if it is chosen *and*
every package in its `requires` is enabled too, checked recursively. If any
requirement is off, the package is off too, and the Packages window shows
`Off: needs <name>`.

Only enabled packages give their `components/` and `tools/` folders to
aniseed. Every discovered package's `hosts/` folder is always used, as the
hosts are what decide which application aniseed is running in.

A requirement that cannot be found at all does not switch the package off.
Instead, aniseed logs a warning when it discovers the packages. The package's
imports will usually fail in that case, so treat the warning as an error.

### Turning on a package turns on its requirements

`aniseed.packages.set_enabled(name, True)` also turns on every package the
named package requires, directly or indirectly, that is not already on.
Turning a package off does not turn off the packages it requires. It does,
however, deactivate any package that requires it.

### Where the choices are stored

The user's choices are saved with scribble under the `aniseed_packages`
identifier, as `{package name: true/false}`. Only packages the user has
changed are stored, and the rest follow their `enabled_by_default`.
`aniseed.packages.reset()` (or **Reset to Defaults**) forgets every choice.

Scripts and tests should not change the user's saved choices. They should
make session-only choices instead, then rebuild the component library and
the rigs, as the Packages window does:

```python
import aniseed

aniseed.packages.set_enabled("aniseed_standard", True, persist=False)
aniseed.Rig.clear_factory_cache()
aniseed.Rig.clear_registry()
```

Session choices take priority over saved choices, and are forgotten when
Maya closes.

### Useful functions

All of these are in `aniseed.packages`:

| Function                             | Returns                                                            |
|--------------------------------------|--------------------------------------------------------------------|
| `discover(refresh=False)`            | Every package found, in priority order.                            |
| `get(name)`                          | The package with that name, or `None`.                             |
| `available()`                        | The packages written for the current host, on or off.              |
| `active()`                           | The packages that are enabled in the current host.                 |
| `is_chosen(package)`                 | Whether the package is turned on, ignoring requirements.           |
| `is_enabled(package)`                | Whether the package is active, including requirements.             |
| `blocking_requirements(package)`     | The required packages that are off, and so keep this one off.      |
| `set_enabled(name, enabled, persist)`| Turns a package on or off.                                         |
| `reset(name=None)`                   | Forgets the choice for one package, or for all of them.            |
