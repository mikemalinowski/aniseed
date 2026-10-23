import os
import json
import typing
import inspect
import logging
import xstack
import crosswalk
import contextlib
import factories
from Qt import QtCore

from . import host as host_
from . import config
from . import component
from . import packages
from . import constants

log = logging.getLogger(__name__)

# -- How long to wait after a change before writing the recipe to the host. A
# -- burst of changes, such as typing into a field, is then written only once.
RECIPE_WRITE_DELAY_MS = 250

# -- The one Rig instance for each host, keyed by the host's name. See
# -- Rig.for_host.
_RIGS: typing.Dict[str, "Rig"] = dict()


# --------------------------------------------------------------------------------------
class Rig(xstack.Stack):
    """
    This class is what represents a rig. It is built upon xstack, and therefore is an
    execution stack. You may add components to the rig and ultimately execute the build
    of that rig.

    There is one Rig instance per host. Use Rig.for_host (or get_rig) to access the
    rig for an existing host, rather than constructing another Rig for it, so that
    scripts and the app share the same instance.

    The recipe stored on the host is not written on every change. A change marks it
    as dirty and it is written once, shortly afterwards. It is always written before
    a build, when the rig is saved to a file, when serialise is called and when the
    rig is disposed. Use flush_recipe to write it straight away.

    Args:
        label: You only need to provide this if you are asking for a new rig to be
            built. This will be the name of the rig

        host: This should be the object that represents the rig. This class will
            auto-populate based on the data stored on that object.

        component_paths: An optional list of paths that should be added to the
            component library
    """

    # -- Components whose type is not available load as this placeholder
    missing_component_class = component.MissingRigComponent

    # ----------------------------------------------------------------------------------
    def __init__(
            self,
            label="",
            host=None,
            configuration: str = None,
            component_paths: typing.Optional[typing.List] = None,
    ):

        # -- Copy the incoming list before mutating it. Without this, if
        # -- the caller hands us a shared list (typically
        # -- ``AppConfig.component_paths`` — a class attribute), every
        # -- Rig construction would append another copy of
        # -- aniseed/components to that shared list. The list would grow
        # -- without bound, and the Factory cache key (which includes the
        # -- paths) would miss every time, forcing a full re-import of
        # -- every component module on every scene change.
        component_paths = list(component_paths) if component_paths else []
        component_paths.append(
            os.path.join(
                os.path.dirname(__file__),
                "components",
            ),
        )

        # -- Add the components from any aniseed packages
        component_paths.extend(packages.component_paths())

        super().__init__(
            label=label,
            component_paths=component_paths,
            component_base_class=component.RigComponent,
        )

        # -- Whether the recipe on the host is out of date, whether a write
        # -- is already scheduled, and how many callers have suspended writes
        self._recipe_dirty = False
        self._recipe_write_scheduled = False
        self._recipe_writes_suspended = 0

        # -- If we're not given a host, then we need to add one
        if not host:
            host = self._create_host(label)

        # -- Store our host as an item rather than a name, so the rig keeps
        # -- working if the host is renamed
        self._host = crosswalk.items.get(host)

        # -- Note: RigConfiguration registration and aniseed env-var paths
        # -- are handled by the cached ``component_library`` property below.

        # -- Load the recipe stored on the host. This is exactly what the host
        # -- already holds, so nothing is written back.
        with self.recipe_writes_suspended():
            self.deserialize(self._read_recipe())

        # -- From now on, any change means the recipe needs writing
        self.changed.connect(
            self.mark_recipe_dirty,
        )

        # -- Become the shared instance for this host, unless there already is one
        if not _registered_rig(self._host):
            _RIGS[crosswalk.items.get_name(self._host)] = self

        # -- If we're given a config and there are not other components
        # -- in the stack, then we add it.
        if not self.components() and configuration:
            self.add_component(
                component_type=configuration,
                label="Configuration",
            )

    # ----------------------------------------------------------------------------------
    @classmethod
    def for_host(cls, host, component_paths: typing.Optional[typing.List] = None) -> "Rig":
        """
        Returns the Rig for the given host, creating it if there is not one yet.

        There is only ever one Rig instance for a host. The app, get_rig, all_rigs
        and scripts all share it, so a change made through one is never
        overwritten by another.

        Args:
            host: The host item (or its name)
            component_paths: Additional component paths, only used if the Rig
                has to be created
        """
        rig = _registered_rig(host)

        if rig:
            return rig

        return cls(host=host, component_paths=component_paths)

    # ----------------------------------------------------------------------------------
    @classmethod
    def flush_all(cls):
        """
        Writes the outstanding recipe changes of every rig. Hosts call this
        before the scene is saved.
        """
        for rig in list(_RIGS.values()):
            rig._flush_recipe_safely()

    # ----------------------------------------------------------------------------------
    @classmethod
    def clear_registry(cls):
        """
        Writes the outstanding recipe changes of every rig, disposes of them and
        forgets them, so the next request for a rig creates a new one. Hosts call
        this before the scene is replaced, as the rigs' hosts are about to stop
        existing.
        """
        for rig in list(_RIGS.values()):
            rig.dispose()

        _RIGS.clear()

    # ----------------------------------------------------------------------------------
    def host(self):
        return self._host

    # ----------------------------------------------------------------------------------
    @property
    def label(self):
        """
        We always want to return the name of the host when getting the label.

        Returns an empty string when the host has been cleared (e.g. via
        :meth:`dispose`), so paint events for tear-down widgets that
        access ``stack.label`` don't blow up on ``get_name(None)``.
        """
        if not self._host:
            return ""
        return crosswalk.items.get_name(self.host())

    # ----------------------------------------------------------------------------------
    @label.setter
    def label(self, v):
        """
        The label is always the name of the host, so setting it does nothing.
        Rename the host to change it.

        This setter exists because ``xstack.Stack`` assigns ``self.label``
        (in ``__init__`` and when deserialising), which would otherwise fail
        on a read-only property.
        """
        return

    # ----------------------------------------------------------------------------------
    def config(self):
        """
        This will return the rig configuration class for the rig
        """
        for component_instance in self.components():
            if component_instance.identifier.startswith("Rig Configuration"):
                return component_instance

        log.warning("could not locate configuration component")
        return None

    # ----------------------------------------------------------------------------------
    def serialise(self) -> typing.Dict:
        """
        We subclass the serialise function so that we can take the serialised
        data and store it within the host object. The recipe is written
        straight away, along with the version of aniseed and of each active
        aniseed package.
        """
        data = super().serialise()
        data["versions"] = self._versions()

        if self._host:
            self._write_recipe(data)

        return data

    # ----------------------------------------------------------------------------------
    @staticmethod
    def _versions() -> typing.Dict:
        """
        Returns the version of aniseed and of each active aniseed package, to
        store alongside the recipe
        """
        return dict(
            aniseed=constants.VERSION,
            packages={
                package.name: package.version
                for package in packages.active()
            },
        )

    # ----------------------------------------------------------------------------------
    def _read_recipe(self) -> typing.Dict:
        """
        Returns the recipe stored on the host, or an empty dictionary if the
        host does not have one (such as a legacy host)
        """
        if not crosswalk.attributes.has_attribute(self.host(), "recipe"):
            return dict()

        return json.loads(
            crosswalk.attributes.get_value(
                self.host(),
                "recipe",
            ) or "{}"
        )

    # ----------------------------------------------------------------------------------
    def _write_recipe(self, data: typing.Dict):
        """
        Stores the given recipe data on the host. The write is not undoable, so
        undo only ever steps through the user's own changes.
        """
        recipe = json.dumps(data)

        with host_.get().without_undo():

            # -- Legacy hosts, or hosts not originally created by aniseed,
            # -- may not have the attribute yet
            if not crosswalk.attributes.has_attribute(self.host(), "recipe"):
                crosswalk.attributes.add_string_attribute(
                    item=self.host(),
                    attribute_name="recipe",
                    value=recipe,
                )

            else:
                crosswalk.attributes.set_value(
                    item=self.host(),
                    attribute_name="recipe",
                    value=recipe,
                )

        self._recipe_dirty = False

    # ----------------------------------------------------------------------------------
    @contextlib.contextmanager
    def recipe_writes_suspended(self):
        """
        Context manager within which changes do not mark the recipe as dirty.
        Use it around changes which do not need writing to the host, such as
        loading the recipe the host already holds.
        """
        self._recipe_writes_suspended += 1

        try:
            yield

        finally:
            self._recipe_writes_suspended -= 1

    # ----------------------------------------------------------------------------------
    def mark_recipe_dirty(self, *args, **kwargs):
        """
        Flags that the recipe on the host is out of date. It is written once,
        shortly afterwards, when a Qt application is running, or straight away
        when there is no event loop to defer it to.
        """
        if self._recipe_writes_suspended or not self._host:
            return

        self._recipe_dirty = True

        if self._recipe_write_scheduled:
            return

        if QtCore.QCoreApplication.instance() is None:
            self.flush_recipe()
            return

        self._recipe_write_scheduled = True
        QtCore.QTimer.singleShot(RECIPE_WRITE_DELAY_MS, self._deferred_flush)

    # ----------------------------------------------------------------------------------
    def flush_recipe(self):
        """
        Writes the recipe to the host now if it has changes which have not been
        written yet
        """
        if self._recipe_dirty and self._host:
            self.serialise()

    # ----------------------------------------------------------------------------------
    def _deferred_flush(self):
        self._recipe_write_scheduled = False
        self._flush_recipe_safely()

    # ----------------------------------------------------------------------------------
    def _flush_recipe_safely(self):
        """
        Flushes the recipe, logging rather than raising if the host can no
        longer be written to (such as if it was deleted)
        """
        try:
            self.flush_recipe()

        except (RuntimeError, ValueError):
            log.exception(f"Failed to write the recipe for {self.label}")

    # ----------------------------------------------------------------------------------
    @classmethod
    def _create_host(cls, name: str):
        """
        This will create the host object within the applications scene. It ensures the host
        has the right attributes to be able to store its serialised
        """
        host = crosswalk.items.create(
            name=name,
        )

        crosswalk.attributes.add_float_attribute(
            item=host,
            attribute_name="aniseed_rig",
            value=1,
        )

        crosswalk.attributes.add_string_attribute(
            item=host,
            attribute_name="recipe",
            value="{}"
        )

        return host

    # ----------------------------------------------------------------------------------
    # noinspection PyBroadException
    def build(
        self,
        build_up_to: str = None,
        build_only: str = None,
        build_below: str = None,
        validate_only: bool = False
    ) -> bool:
        """
        We re-implement the build to allow us to check whether we have a rig configuration
        component in a stack. If we do not, or if it is not valid then we do not allow
        the build to continue.

        The recipe is written to the host before the build starts, and the build
        runs within the host's build_context (in Maya, a single undo step).
        """
        configuration = self.config()

        if not configuration:
            return self._refuse_build(
                None,
                "No configuration component found. You must have one in order to build",
            )

        # -- We also need to check that it is valid. But not, its possible this could be
        # -- third party code, so we wrap it in a broad exception
        try:
            is_valid = configuration.is_valid()

        except Exception:
            log.exception(f"Failed to run validation for {configuration.label()}")
            is_valid = False

        if not is_valid:
            return self._refuse_build(
                configuration,
                "Failed to validate the rig configuration. Stopping build.",
            )

        self.flush_recipe()

        with host_.get().build_context(self):
            return super().build(
                build_up_to,
                build_only,
                build_below,
                validate_only,
            )

    # ----------------------------------------------------------------------------------
    def _refuse_build(self, failed_component, reason: str) -> bool:
        """
        Reports a build which could not start, in the same way as a failed build
        """
        log.warning(reason)

        if not self.is_building():
            self.build_failed.emit(failed_component, reason)
            self.build_finished.emit(False)

        return False

    # ----------------------------------------------------------------------------------
    @classmethod
    def all_rigs(cls):
        """
        This will return the Rig for every rig host in the scene
        """
        return [
            cls.for_host(rig_host)
            for rig_host in crosswalk.items.all_items_with_attribute("aniseed_rig")
        ]

    # ----------------------------------------------------------------------------------
    def deserialize(self, data: typing.Union[str, typing.Dict], clear: bool = True):
        """
        Loads the given recipe (or the json file at the given path) into this
        rig. The recipe on the host is then written once, rather than once per
        component.
        """
        if isinstance(data, str):
            with open(data, 'r') as f:
                data = json.load(f)

        with self.recipe_writes_suspended():

            # -- Remove any existing components first. Some components delete scene
            # -- nodes (such as their joints) when removed, so this must happen
            # -- before the host restores anything into the scene.
            if clear:
                self.clear()

            # -- Call the host callback - which allows an embedded environment
            # -- to tie into the load process. This happens before the components
            # -- are added so that anything the host restores (such as the saved
            # -- skeleton) already exists when each component's on_deserialise runs.
            host_app = host_.get()
            host_app.on_rig_load(
                self,
                data,
            )

            # -- Call the parent class which manages the load. It has already
            # -- been cleared above.
            super().deserialize(data, clear=False)

        # -- The file level "additional_data" (such as the skeleton hierarchy the
        # -- host restores) is only used at the moment a file is loaded. It is
        # -- not part of serialise, so it never reaches the host. Otherwise every
        # -- later Rig created for this node would restore it again, duplicating
        # -- the skeleton.
        self.mark_recipe_dirty()

    # ----------------------------------------------------------------------------------
    def save(
        self,
        filepath: str,
        additional_data: typing.Optional[typing.Dict] = None,
    ):
        # -- Before saving, check if the host callback wants to provide
        # -- any additional data to store in the save file
        host_app = host_.get()
        host_data = host_app.on_rig_save(rig=self) or dict()

        # -- Combine the additional data
        additional_data = additional_data or dict()
        additional_data.update(host_data)

        # -- Finally save the file. This serialises, so the host's recipe is
        # -- written too.
        super().save(
            filepath,
            additional_data,
        )

    # ----------------------------------------------------------------------------------
    def execute_block(self, block_name):
        """
        This will execute an execution block by its label
        """
        for execute_block in self.components(of_type="Stack : Execution Block"):
            if execute_block.label() == block_name:
                return self.build(build_below=execute_block)

    # ----------------------------------------------------------------------------------
    def _signals(self) -> typing.List:
        """
        Returns the rig level signals
        """
        return [
            self.changed,
            self.component_added,
            self.component_removed,
            self.hierarchy_changed,
            self.build_started,
            self.build_progressed,
            self.build_completed,
            self.build_finished,
            self.build_failed,
            self.component_reporting,
        ]

    # ----------------------------------------------------------------------------------
    def detach_listeners(self):
        """
        Disconnects everything listening to the rig level signals, such as a UI
        which showed the rig, whilst leaving the rig fully working. Use this when
        a UI stops showing a rig which is still in use.
        """
        for signal in self._signals():
            signal.disconnect()

        self.changed.connect(self.mark_recipe_dirty)

    # ----------------------------------------------------------------------------------
    def dispose(self):
        """
        Writes any outstanding recipe changes, then aggressively tears down
        internal signal connections and parent/child cross-references so the
        rig, its components, and the widgets that were connected to its signals
        all become refcount-collectable immediately — without waiting for
        Python's cyclic GC. The rig is also removed from the registry.

        Two reasons this matters:

        1. **Safety.** The rig's ``changed -> mark_recipe_dirty`` chain writes
           to the Maya host attribute. After scene close the host
           MObject is invalid, so any later emit would crash Maya.
        2. **Speed.** Without aggressive disposal, every scene
           transition leaves a generation of cycle garbage (50+
           Components × signal tables × widgets), and the next
           transition pays a growing GC cost. Empirically this added
           ~0.7s per scene change.

        After dispose the rig is gutted — calling anything on it
        (``components()``, ``serialise()``) will return empty/None.
        Nothing should be calling a disposed rig.
        """
        if self._host:
            self._flush_recipe_safely()

        for name, rig in list(_RIGS.items()):
            if rig is self:
                del _RIGS[name]

        # -- Snapshot the component list before we mutate the tree.
        components = list(self.components())

        # -- Clear per-component signal tables (and break parent/child
        # -- cycles), so each Component drops its references to the
        # -- rig, to other components, and to whatever widgets had
        # -- listeners connected to it.
        for c in components:
            c.changed.disconnect()
            for attr in list(c.options()) + list(c.inputs()) + list(c.outputs()):
                attr.value_changed.disconnect()
            c.parent = None
            c.children = []

        # -- Clear the rig's own signal tables.
        for signal in self._signals():
            signal.disconnect()

        # -- Drop the rig's structural references to components and
        # -- the host.
        self.root_components = []
        self._host = None
        self._recipe_dirty = False

    # ----------------------------------------------------------------------------------
    # -- Class-level Factory cache. Component discovery is the dominant
    # -- cost of instantiating a Rig (importing ~hundreds of component
    # -- modules from disk takes ~10s+ in a studio-sized install). We
    # -- override xstack.Stack.component_library here to share a single
    # -- Factory across every Rig built from the same paths, so the
    # -- first Rig in a session pays the cost and every subsequent Rig
    # -- — including each scene-switch — is effectively instant.
    _FACTORY_CACHE: typing.Dict[tuple, "factories.Factory"] = {}

    @property
    def component_library(self) -> "factories.Factory":
        """
        Returns the component factory for this rig.

        Cached at the class level, keyed by ``(base_class, sorted paths)``.
        Paths include the rig's ``component_paths`` plus both the xstack
        and aniseed env-var path lists, so add_path doesn't need to be
        called separately after construction.

        If you've edited a component .py file on disk and want the
        running session to pick it up, call
        :meth:`Rig.clear_factory_cache` — or use the Reload menu, which
        drops the aniseed modules entirely and forces a full re-scan.
        """
        paths = self.component_paths[:]
        paths.extend(
            os.environ.get(xstack.constants.COMPONENT_PATHS_ENVVAR, "").split(",")
        )
        paths.extend(
            packages.split_paths(os.environ.get(constants.RIG_COMPONENTS_PATHS_ENVVAR, ""))
        )
        # -- Dedupe via set, then sort, so duplicates in the input list
        # -- (or different ordering) hit the same cache entry.
        paths = tuple(
            sorted(
                {
                    p
                    for p in paths
                    if p
                }
            )
        )

        key = (self.component_base_class, paths)
        cached = Rig._FACTORY_CACHE.get(key)
        if cached is None:
            cached = factories.Factory(
                abstract=self.component_base_class,
                paths=list(paths),
                plugin_identifier="identifier",
            )
            cached.register(config.RigConfiguration)
            self._warn_duplicate_identifiers(cached)
            Rig._FACTORY_CACHE[key] = cached

        return cached

    # ----------------------------------------------------------------------------------
    @staticmethod
    def _warn_duplicate_identifiers(library: "factories.Factory"):
        """
        Component identifiers must be unique across aniseed and every aniseed
        package. Where two components share one, the factory returns whichever
        it found first, so we warn rather than let one silently replace the other.
        """
        # -- The factory imports each component file under a unique module name,
        # -- so a component file that another component module imports through
        # -- its package path (to subclass it, say) is executed twice and gives
        # -- a second class object. That is the same component, not a clash, so
        # -- count each class once by its source file and name.
        unique_plugins = {}

        for plugin in library._plugins:
            try:
                source = os.path.normcase(os.path.abspath(inspect.getfile(plugin)))
            except TypeError:
                source = plugin.__module__

            unique_plugins.setdefault((source, plugin.__qualname__), plugin)

        identifiers = [
            library._get_identifier(plugin)
            for plugin in unique_plugins.values()
        ]

        for identifier in sorted(set(identifiers)):
            if identifiers.count(identifier) > 1:
                log.warning(
                    f"{identifiers.count(identifier)} components share the identifier "
                    f"'{identifier}'. Component identifiers must be unique."
                )

    # ----------------------------------------------------------------------------------
    @classmethod
    def clear_factory_cache(cls):
        """
        Drop the class-level component-Factory cache, so the next Rig created
        scans the component paths again and loads each component module from
        disk.

        Rigs which already exist keep the component classes they were created
        with, and the modules components import (such as aniseed_toolkit or a
        package's mixins) are not reloaded. Use the Reload menu, which also
        drops those modules and the existing rigs, to pick up those changes.
        """
        cls._FACTORY_CACHE.clear()


# --------------------------------------------------------------------------------------
def _registered_rig(host) -> typing.Optional[Rig]:
    """
    Returns the registered Rig for the given host, or None if there is not one.
    Rigs which were disposed, or whose host no longer exists, are forgotten, and
    a rig whose host was renamed is found under its new name.
    """
    name = crosswalk.items.get_name(host)
    rig = _RIGS.get(name)

    if rig and _is_rig_for(rig, name):
        return rig

    # -- Rebuild the registry from the current name of each rig's host
    live_rigs = dict()

    for rig in _RIGS.values():
        if not rig.host():
            continue

        # -- The host may no longer exist, so its name may not be readable
        try:
            rig_name = rig.label

        except (RuntimeError, ValueError):
            continue

        if _is_rig_for(rig, rig_name):
            live_rigs[rig_name] = rig

    _RIGS.clear()
    _RIGS.update(live_rigs)

    return _RIGS.get(name)


# --------------------------------------------------------------------------------------
def _is_rig_for(rig: Rig, name: str) -> bool:
    """
    Returns True if the item called name exists and is the rig's host
    """
    if not rig.host() or not crosswalk.items.exists(name):
        return False

    return crosswalk.items.get(name) == rig.host()


# --------------------------------------------------------------------------------------
def get_rig(node):
    """
    This is a convenient function for getting the Rig class for a
    node within its rig hierarchy. The Rig returned is the same instance the
    app uses, so changes made through it are not overwritten by the app.

    For instance, the following example is how a rig which has nodes to
    separate the edit/build functionality can easily be accessed and built.


    >>> # -- Import aniseed. We'll also use crosswalk just to make this
    >>> # -- example work in any supported application
    >>> import aniseed
    >>> import crosswalk
    >>>
    >>> # -- Get the rig instance
    >>> rig = aniseed.get_rig(crosswalk.selection.selected()[0])
    >>>
    >>> # -- Find the two components we're interested in
    >>> build_rig = rig.get_component_by_label("Build Control Rig")
    >>> make_editable = rig.get_component_by_label("Make Rig Editable")
    >>>
    >>> # -- Lets start by making the rig editable
    >>> rig.build(build_below=make_editable)
    >>>
    >>> # -- Now lets build the control rig
    >>> rig.build(build_below=build_rig)
    """
    current = node
    while current is not None:
        if crosswalk.attributes.has_attribute(current, "aniseed_rig"):
            return Rig.for_host(current)
        current = crosswalk.items.get_parent(current)

    return None
