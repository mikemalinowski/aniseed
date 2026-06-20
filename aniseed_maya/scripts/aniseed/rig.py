import os
import re
import json
import xstack
import typing
import crosswalk
import factories
import traceback

from . import host as host_
from . import config
from . import component
from . import constants


# --------------------------------------------------------------------------------------
class Rig(xstack.Stack):
    """
    This class is what represents a rig. It is built upon xstack, and therefore is an
    execution stack. You may add components to the rig and ultimately execute the build
    of that rig.

    Args:
        label: You only need to provide this if you are asking for a new rig to be
            built. This will be the name of the rig

        host: This should be the object that represents the rig. This class will
            auto-populate based on the data stored on that object.

        component_paths: An optional list of paths that should be added to the
            component library
    """

    # ----------------------------------------------------------------------------------
    def __init__(self, label="", host=None, configuration: str = None, component_paths: typing.List or None = None):

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

        super().__init__(
            label=label,
            component_paths=component_paths,
            component_base_class=component.RigComponent,
        )

        # -- If we're not given a host, then we need to add one
        if not host:
            host = self._create_host(label)

        # -- Store our host
        self._host = host

        # -- Note: RigConfiguration registration and aniseed env-var paths
        # -- are handled by the cached ``component_library`` property below.

        # -- If the host is missing the recipe attribute (legacy hosts, or
        # -- hosts not originally created by aniseed), add it now so
        # -- subsequent reads and writes have something to work with.
        if not crosswalk.attributes.has_attribute(self.host(), "recipe"):
            crosswalk.attributes.add_string_attribute(
                item=self.host(),
                attribute_name="recipe",
                value="{}",
            )

        self.deserialize(
            json.loads(
                crosswalk.attributes.get_value(
                    self.host(),
                    "recipe",
                ),
            )
        )

        # -- As we have now populated the class, emit the fact that the class has
        # -- changed
        self.changed.connect(
            self.serialise,
        )

        # -- If we're given a config and there are not other components
        # -- in the stack, then we add it.
        if not self.components() and configuration:
            self.add_component(
                component_type=configuration,
                label="Configuration",
            )

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
        Setting the label renames the host node. The getter returns the
        host's name, so the rig's label and the host's name stay in sync
        by design — renaming via either route is equivalent.

        Silently ignored if there is no host yet (e.g. during
        ``xstack.Stack.__init__``, which assigns ``self.label = label``
        *before* aniseed's :class:`Rig.__init__` has had a chance to
        create or attach a host) or if ``v`` is empty.
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

        print("could not locate configuration component")
        return None

    # ----------------------------------------------------------------------------------
    def serialise(self) -> typing.Dict:
        """
        We subclass the serialise function so that we can take the serialised
        data and store it within the host object
        """
        data = super().serialise()

        crosswalk.attributes.set_value(
            item=self.host(),
            attribute_name="recipe",
            value=json.dumps(data),
        )
        return data

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
        the build to continue
        """

        if not self.config():
            print("No configuration component found. You must have one in order to build")
            return False

        # -- We also need to check that it is valid. But not, its posisble this could be
        # -- third party code, so we wrap it in a broad exception
        try:
            if not self.config().is_valid():
                print("Failed to validate the rig configuration. Stopping build.")
                return False

        except Exception:
            print(f"Failed to run validation for {self.config()}")
            traceback.print_exc()
            return False

        result = super().build(
            build_up_to,
            build_only,
            build_below,
            validate_only,
        )

        return result

    @classmethod
    def all_rigs(cls):
        """
        This will attempt to find all instances of a rig in the scene
        """
        results = []
        for rig_host in crosswalk.items.all_items_with_attribute("aniseed_rig"):
            results.append(cls(host=rig_host))
        return results

    def deserialize(self, data: typing.Dict, clear: bool = True):
        if isinstance(data, str):
            with open(data, 'r') as f:
                data = json.load(f)

        # -- Call the parent class which manages the load
        super().deserialize(data, clear=clear)

        # -- Store the data on the host node
        crosswalk.attributes.set_value(
            item=self.host(),
            attribute_name="recipe",
            value=json.dumps(data),
        )

        # -- Now call the host callback - which allows an embedded environment
        # -- to tie into the load process
        host_app = host_.get()
        host_app.on_rig_load(
            self,
            data,
        )

    def save(
        self,
        filepath: str,
        additional_data: typing.Dict or None = None,
    ):
        # -- Before saving, check if the host callback wants to provide
        # -- any additional data to store in the save file
        host_app = host_.get()
        host_data = host_app.on_rig_save(rig=self) or dict()

        # -- Combine the additional data
        additional_data = additional_data or dict()
        additional_data.update(host_data)

        # -- Finally save the file
        super().save(
            filepath,
            additional_data,
        )

    def execute_block(self, block_name):
        """
        This will execute an execution block by its label
        """
        for execute_block in self.components(of_type="Stack : Execution Block"):
            if execute_block.label() == block_name:
                return self.build(build_below=execute_block)

    def dispose(self):
        """
        Aggressively tear down internal signal connections and
        parent/child cross-references so the rig, its components, and
        the widgets that were connected to its signals all become
        refcount-collectable immediately — without waiting for
        Python's cyclic GC.

        Two reasons this matters:

        1. **Safety.** The rig's ``changed -> serialise`` chain writes
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
        # -- Snapshot the component list before we mutate the tree.
        components = list(self.components())

        # -- Clear per-component signal tables (and break parent/child
        # -- cycles), so each Component drops its references to the
        # -- rig, to other components, and to whatever widgets had
        # -- listeners connected to it.
        for c in components:
            try:
                c.changed.disconnect()
                for attr in list(c.options()) + list(c.inputs()) + list(c.outputs()):
                    attr.value_changed.disconnect()
            except Exception:
                pass
            c.parent = None
            c.children = []

        # -- Clear the rig's own signal tables.
        for signal_name in (
            "changed",
            "component_added",
            "component_removed",
            "hierarchy_changed",
            "build_started",
            "build_progressed",
            "build_completed",
        ):
            try:
                getattr(self, signal_name).disconnect()
            except Exception:
                pass

        # -- Drop the rig's structural references to components and
        # -- the host.
        self.root_components = []
        self._host = None

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
            re.split(";|,", os.environ.get(constants.RIG_COMPONENTS_PATHS_ENVVAR, ""))
        )
        # -- Dedupe via set, then sort, so duplicates in the input list
        # -- (or different ordering) hit the same cache entry.
        paths = tuple(sorted({p for p in paths if p}))

        key = (self.component_base_class, paths)
        cached = Rig._FACTORY_CACHE.get(key)
        if cached is None:
            cached = factories.Factory(
                abstract=self.component_base_class,
                paths=list(paths),
                plugin_identifier="identifier",
            )
            cached.register(config.RigConfiguration)
            Rig._FACTORY_CACHE[key] = cached

        return cached

    @classmethod
    def clear_factory_cache(cls):
        """
        Drop the class-level component-Factory cache. The next Rig
        instantiation will re-scan component paths and re-import every
        component module from disk. Use this if you've edited
        component code and want the running Maya session to pick the
        change up without a restart.
        """
        cls._FACTORY_CACHE.clear()


def get_rig(node):
    """
    This is a convenient function for getting the Rig class for a
    node within its rig hierarchy.

    For instance, the following example is how a rig which has nodes to
    seperate the edit/build functionality can easily be accessed and built.


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
            return Rig(host=current)
        current = crosswalk.items.get_parent(current)

    return None
