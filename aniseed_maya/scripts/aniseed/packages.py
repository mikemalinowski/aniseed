"""
Aniseed packages are folders which contribute components, mixins, widgets
and hosts to aniseed, keeping all application specific code out of the core.

A package is any folder containing an aniseed_package.json marker file, and
the folder name is the package name. Within it, aniseed looks for these
optional folders:

    components/ : added to the component factory paths
    hosts/      : added to the embedded host factory paths
    mixins/     : importable as <package_name>.mixins
    widgets/    : importable as <package_name>.widgets
    tools/      : searched by aniseed_toolkit for aniseed_toolkit.Tool's

Packages are searched for in each path of the ANISEED_PACKAGE_PATHS
environment variable, and then alongside the aniseed module itself. Each
of those paths may either be a package, or a folder of packages.

Packages can be turned on and off (through Edit > Packages in the app, or
set_enabled). A package is enabled unless its marker file sets
"enabled_by_default" to false, or the user has turned it off. Packages which
provide a host are always enabled, and a package is only active if every
package it requires is too.
"""
import os
import re
import sys
import json
import typing
import logging

import scribble

from . import constants

log = logging.getLogger(__name__)


MARKER = "aniseed_package.json"

# -- The scribble identifier the user's choice of enabled packages is saved
# -- under, as {package name: True/False}
SETTINGS_ID = "aniseed_packages"

# -- Choices which only last for this session, made with
# -- set_enabled(persist=False). These take priority over the saved choices.
_SESSION_CHOICES: typing.Dict[str, bool] = dict()


# --------------------------------------------------------------------------------------
class AniseedPackage:
    """
    Represents a single aniseed package on disk.

    The marker file may optionally contain any of the following:

        hosts: list of host names (such as "maya") this package is
            written for. If empty, the package is used in every host.

        requires: list of package names this package depends on

        version: the version of the package

        description: a short description of the package

        enabled_by_default: whether the package is enabled until the user
            chooses otherwise. Defaults to true.
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, root: str):
        self.root = root
        self.name = os.path.basename(root)
        self.metadata = self._read_metadata()

    # ----------------------------------------------------------------------------------
    def __repr__(self):
        return f"<AniseedPackage {self.name} ({self.root})>"

    # ----------------------------------------------------------------------------------
    def _read_metadata(self) -> typing.Dict:
        try:
            with open(os.path.join(self.root, MARKER), "r") as f:
                return json.load(f) or dict()

        except ValueError:
            log.warning(f"Could not read {MARKER} in {self.root}, treating it as empty")
            return dict()

    # ----------------------------------------------------------------------------------
    def _sub_folder(self, folder_name: str) -> typing.Optional[str]:
        path = os.path.join(self.root, folder_name)
        return path if os.path.isdir(path) else None

    # ----------------------------------------------------------------------------------
    @property
    def components(self) -> typing.Optional[str]:
        return self._sub_folder("components")

    # ----------------------------------------------------------------------------------
    @property
    def mixins(self) -> typing.Optional[str]:
        return self._sub_folder("mixins")

    # ----------------------------------------------------------------------------------
    @property
    def widgets(self) -> typing.Optional[str]:
        return self._sub_folder("widgets")

    # ----------------------------------------------------------------------------------
    @property
    def hosts(self) -> typing.Optional[str]:
        return self._sub_folder("hosts")

    # ----------------------------------------------------------------------------------
    @property
    def tools(self) -> typing.Optional[str]:
        return self._sub_folder("tools")

    # ----------------------------------------------------------------------------------
    @property
    def version(self) -> str:
        return self.metadata.get("version", "")

    # ----------------------------------------------------------------------------------
    @property
    def requires(self) -> typing.List[str]:
        return self.metadata.get("requires", list())

    # ----------------------------------------------------------------------------------
    @property
    def description(self) -> str:
        return self.metadata.get("description", "")

    # ----------------------------------------------------------------------------------
    @property
    def enabled_by_default(self) -> bool:
        return bool(self.metadata.get("enabled_by_default", True))

    # ----------------------------------------------------------------------------------
    def can_disable(self) -> bool:
        """
        Returns False for packages which provide a host. Turning one off would
        remove aniseed's menu, window and undo support from that application,
        so they are always enabled.
        """
        return self.hosts is None

    # ----------------------------------------------------------------------------------
    def supports_host(self, host_name: str) -> bool:
        """
        Returns True if this package should be used within the given host
        """
        supported_hosts = self.metadata.get("hosts", list())
        return not supported_hosts or host_name in supported_hosts


# -- Packages are discovered once and then cached for the session
_PACKAGES: typing.Optional[typing.List[AniseedPackage]] = None


# --------------------------------------------------------------------------------------
def split_paths(value: str) -> typing.List[str]:
    """
    Splits an environment variable value into its paths. We split on ; and ,
    rather than os.pathsep, as : appears within windows drive letters.
    """
    return [path for path in re.split(";|,", value or "") if path]


# --------------------------------------------------------------------------------------
def search_roots() -> typing.List[str]:
    """
    Returns the locations to search for packages, in priority order.
    """
    roots = split_paths(os.environ.get(constants.ANISEED_PACKAGE_PATHS_ENVVAR, ""))

    # -- By default we always look alongside the aniseed module
    roots.append(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return roots


# --------------------------------------------------------------------------------------
def is_package(path: str) -> bool:
    return os.path.isfile(os.path.join(path, MARKER))


# --------------------------------------------------------------------------------------
def discover(refresh: bool = False) -> typing.List[AniseedPackage]:
    """
    Returns every aniseed package, in priority order. The result is cached,
    so disk is only searched again when refresh is True.

    Discovering a package makes it importable by its name.
    """
    global _PACKAGES

    if _PACKAGES is not None and not refresh:
        return _PACKAGES

    packages = []

    for root in search_roots():

        if not os.path.isdir(root):
            continue

        # -- A search root can either be a package itself, or a folder
        # -- of packages
        if is_package(root):
            candidates = [root]

        else:
            candidates = [
                os.path.join(root, folder_name)
                for folder_name in sorted(os.listdir(root))
            ]

        for candidate in candidates:

            if not is_package(candidate):
                continue

            package = AniseedPackage(candidate)

            # -- Packages are imported by their name, so it must be a valid
            # -- python module name
            if not package.name.isidentifier():
                log.warning(f"Skipping aniseed package {candidate}: {package.name} is not a valid python name")
                continue

            # -- Only one package of any given name can be imported, so the
            # -- higher priority package wins
            existing = get(package.name, packages)
            if existing:
                log.warning(f"Skipping aniseed package {candidate}: {package.name} is already provided by {existing.root}")
                continue

            packages.append(package)
            _register_python_path(package)

    # -- Warn about any packages whose requirements are missing
    names = [package.name for package in packages]
    for package in packages:
        for required_name in package.requires:
            if required_name not in names:
                log.warning(f"Aniseed package {package.name} requires {required_name}, which could not be found")

    _PACKAGES = packages
    return packages


# --------------------------------------------------------------------------------------
def _register_python_path(package: AniseedPackage):
    """
    We add the folder containing the package (rather than each of the package's
    folders) to the python path, so that the package is imported by its name
    (my_package.mixins). This prevents package modules such as hosts/maya.py
    from shadowing real modules, and prevents packages clashing with each other.
    """
    parent = os.path.dirname(package.root)

    if parent not in sys.path:
        sys.path.append(parent)


# --------------------------------------------------------------------------------------
def get(name: str, packages: typing.Optional[typing.List[AniseedPackage]] = None) -> typing.Optional[AniseedPackage]:
    """
    Returns the package with the given name
    """
    for package in discover() if packages is None else packages:
        if package.name == name:
            return package
    return None


# --------------------------------------------------------------------------------------
def available() -> typing.List[AniseedPackage]:
    """
    Returns the packages written for the current host, whether or not they
    are enabled
    """
    # -- Imported here to break the import cycle, as host imports this module
    from . import host

    host_name = host.get().name

    return [
        package
        for package in discover()
        if package.supports_host(host_name)
    ]


# --------------------------------------------------------------------------------------
def active() -> typing.List[AniseedPackage]:
    """
    Returns the packages which should be used within the current host: those
    which are written for it and are enabled (see is_enabled)
    """
    packages = available()
    choices = _choices()

    return [
        package
        for package in packages
        if _is_enabled(package, packages, choices)
    ]


# --------------------------------------------------------------------------------------
def is_chosen(package: AniseedPackage) -> bool:
    """
    Returns whether the package is turned on, by the user's choice or (if
    they have not made one) its enabled_by_default. Requirements are not
    taken into account: use is_enabled for that.
    """
    return _is_chosen(package, _choices())


# --------------------------------------------------------------------------------------
def is_enabled(package: AniseedPackage) -> bool:
    """
    Returns whether the package is active: it is turned on, and so is every
    package it requires (as far as those packages are available)
    """
    return _is_enabled(package, available(), _choices())


# --------------------------------------------------------------------------------------
def blocking_requirements(package: AniseedPackage) -> typing.List[str]:
    """
    Returns the names of the packages this package requires which are
    available but not enabled, and so stop it from being active
    """
    packages = available()
    choices = _choices()

    return [
        required.name
        for required in packages
        if required.name in package.requires
        and not _is_enabled(required, packages, choices)
    ]


# --------------------------------------------------------------------------------------
def set_enabled(name: str, enabled: bool, persist: bool = True) -> None:
    """
    Turns a package on or off. Turning a package on also turns on the
    packages it requires.

    Changing this does not affect rigs which already exist. Clear the
    component library and the rigs (as the Packages window does) for the
    change to take effect.

    Args:
        name: The name of the package.
        enabled: True to turn it on, False to turn it off.
        persist: If True, the choice is saved for this user. If False, it
            only lasts for this session, which suits scripts and tests.

    Raises:
        ValueError: If there is no package with the name, or it provides a
            host and so cannot be turned off.
    """
    package = get(name)

    if package is None:
        raise ValueError(f"There is no aniseed package called {name!r}")

    if not enabled and not package.can_disable():
        raise ValueError(f"{name} provides a host, so it cannot be turned off")

    names = [name]

    if enabled:
        # -- Only record requirements which are not already on (which also
        # -- skips host packages, as they are always on), so turning one
        # -- package on never pins the choice for others needlessly
        choices = _choices()
        names.extend(
            required
            for required in _requirements(package)
            if not _is_chosen(get(required), choices)
        )

    if persist:
        settings = scribble.get(SETTINGS_ID)
        for each in names:
            settings[each] = bool(enabled)
            _SESSION_CHOICES.pop(each, None)
        settings.save()

    else:
        for each in names:
            _SESSION_CHOICES[each] = bool(enabled)


# --------------------------------------------------------------------------------------
def reset(name: typing.Optional[str] = None) -> None:
    """
    Forgets the saved and session choices for the named package, or for
    every package if no name is given, so each goes back to its
    enabled_by_default.
    """
    settings = scribble.get(SETTINGS_ID)

    for each in [name] if name else list(settings.keys()) + list(_SESSION_CHOICES):
        settings.pop(each, None)
        _SESSION_CHOICES.pop(each, None)

    settings.save()


# --------------------------------------------------------------------------------------
def _choices() -> typing.Dict[str, bool]:
    """
    Returns the user's choices, with this session's choices on top
    """
    choices = dict(scribble.get(SETTINGS_ID))
    choices.update(_SESSION_CHOICES)
    return choices


# --------------------------------------------------------------------------------------
def _is_chosen(package: AniseedPackage, choices: typing.Dict[str, bool]) -> bool:
    if not package.can_disable():
        return True

    return bool(choices.get(package.name, package.enabled_by_default))


# --------------------------------------------------------------------------------------
def _is_enabled(
        package: AniseedPackage,
        packages: typing.List[AniseedPackage],
        choices: typing.Dict[str, bool],
        visiting: typing.Optional[set] = None,
) -> bool:
    """
    Returns True if the package is chosen, and so (recursively) is every
    package it requires. A requirement which is not available is ignored here,
    as discover already warns about it.
    """
    if not _is_chosen(package, choices):
        return False

    # -- Guard against packages which (wrongly) require each other
    visiting = (visiting or set()) | {package.name}

    for required in packages:
        if required.name in package.requires and required.name not in visiting:
            if not _is_enabled(required, packages, choices, visiting):
                return False

    return True


# --------------------------------------------------------------------------------------
def _requirements(package: AniseedPackage, found: typing.Optional[set] = None) -> typing.List[str]:
    """
    Returns the names of every package the given package requires, directly
    or through other packages, which can be found
    """
    found = found if found is not None else set()

    for name in package.requires:
        required = get(name)

        if required is not None and name not in found:
            found.add(name)
            _requirements(required, found)

    return sorted(found)


# --------------------------------------------------------------------------------------
def component_paths() -> typing.List[str]:
    """
    Returns the component folders of all the packages valid for the current host
    """
    return [
        package.components
        for package in active()
        if package.components
    ]


# --------------------------------------------------------------------------------------
def tool_paths() -> typing.List[str]:
    """
    Returns the tool folders of all the packages valid for the current host.
    aniseed does not use these itself - they are searched by aniseed_toolkit.
    """
    return [
        package.tools
        for package in active()
        if package.tools
    ]


# --------------------------------------------------------------------------------------
def host_paths() -> typing.List[str]:
    """
    Returns the host folders of every package. These are not filtered by host,
    as it is the hosts which determine which host we are in.
    """
    return [
        package.hosts
        for package in discover()
        if package.hosts
    ]
