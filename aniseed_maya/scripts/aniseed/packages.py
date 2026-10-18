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
"""
import os
import re
import sys
import json
import typing

from . import constants


MARKER = "aniseed_package.json"


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
            print(f"Could not read {MARKER} in {self.root}, treating it as empty")
            return dict()

    # ----------------------------------------------------------------------------------
    def _sub_folder(self, folder_name: str) -> str or None:
        path = os.path.join(self.root, folder_name)
        return path if os.path.isdir(path) else None

    # ----------------------------------------------------------------------------------
    @property
    def components(self) -> str or None:
        return self._sub_folder("components")

    # ----------------------------------------------------------------------------------
    @property
    def mixins(self) -> str or None:
        return self._sub_folder("mixins")

    # ----------------------------------------------------------------------------------
    @property
    def widgets(self) -> str or None:
        return self._sub_folder("widgets")

    # ----------------------------------------------------------------------------------
    @property
    def hosts(self) -> str or None:
        return self._sub_folder("hosts")

    # ----------------------------------------------------------------------------------
    @property
    def tools(self) -> str or None:
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
    def supports_host(self, host_name: str) -> bool:
        """
        Returns True if this package should be used within the given host
        """
        supported_hosts = self.metadata.get("hosts", list())
        return not supported_hosts or host_name in supported_hosts


# -- Packages are discovered once and then cached for the session
_PACKAGES: typing.List[AniseedPackage] or None = None


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
                print(f"Skipping aniseed package {candidate}: {package.name} is not a valid python name")
                continue

            # -- Only one package of any given name can be imported, so the
            # -- higher priority package wins
            existing = get(package.name, packages)
            if existing:
                print(f"Skipping aniseed package {candidate}: {package.name} is already provided by {existing.root}")
                continue

            packages.append(package)
            _register_python_path(package)

    # -- Warn about any packages whose requirements are missing
    names = [package.name for package in packages]
    for package in packages:
        for required_name in package.requires:
            if required_name not in names:
                print(f"Aniseed package {package.name} requires {required_name}, which could not be found")

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
def get(name: str, packages: typing.List[AniseedPackage] or None = None) -> AniseedPackage or None:
    """
    Returns the package with the given name
    """
    for package in discover() if packages is None else packages:
        if package.name == name:
            return package
    return None


# --------------------------------------------------------------------------------------
def active() -> typing.List[AniseedPackage]:
    """
    Returns the packages which should be used within the current host
    """
    from . import host

    host_name = host.get().name

    return [
        package
        for package in discover()
        if package.supports_host(host_name)
    ]


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
