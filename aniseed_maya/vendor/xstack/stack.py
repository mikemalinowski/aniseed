import os
import copy
import time
import json
import typing
import logging
import functools
import traceback
import factories
import signalling

from . import constants
from . import compat
from . import address
from .constants import Status
from .component import Component
from .component import MissingComponent

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
class Stack:
    """
    This class is the main class of stackx and represents the actual stack object.

    This is typically the class you will interact with and utilise to add components
    to the stack.

    Args:
        label: This is a human-readable identifier for the stack that has no bearing
        component_paths: A list of paths that should be added to the component library
            when the stack is instanced
        component_base_class: This allows for any subclassing of the Stack object to
            specify their own base class for components. Note, that if you do pass a
            custom base class, your base class must still inherit from Component class.

    This class exposes a series of signals to help intergrate it into UI elements or
    other frameworks. These are:

    component_added(component_instance): Emitted after a component has been added to
        the stack

    component_removed(component_instance): Emitted after a component has been
        removed from the stack. Note, that this component will not show any more
        in Stack.components()

    hierarchy_changed(): Emitted when an item is moved in the hierarchy or build order.

    changed(): Emitted whenever a component is added or removed or the build order
        is changed in any way.

    build_started(): Emitted when a build (or validation) starts.

    build_progressed(percentage): Emitted as each component is built.

    build_completed(): Emitted when a build completes successfully. It is not
        emitted when a build fails.

    build_finished(successful): Emitted whenever a build (or validation) that
        emitted build_started ends, whether it succeeded or not.

    build_failed(component, details): Emitted before build_finished when a build
        fails, with the first component that failed or was invalid (or None if
        the failure was not down to one component), and the reason as text -
        the traceback if the component raised an exception.

    Builds started from within a component's run (nested builds) emit none of
    the build signals: the outer build reports the overall result.

    component_reporting(component, stage): Emitted just before the build report
        lines for a component are printed, where stage is "validate" or
        "build". Unlike the build signals it is emitted in nested builds too,
        so a listener (such as the app's log) can find each component's part
        of the report.
    """
    status = constants.Status

    # -- The class used to stand in for components whose type is not
    # -- available when loading serialised data
    missing_component_class = MissingComponent

    # ----------------------------------------------------------------------------------
    def __init__(
            self,
            label: str = "",
            component_paths: typing.Optional[typing.List] = None,
            component_base_class=Component
    ):
        super().__init__()

        # -- The label of a stack has no functional bearing, but can be useful
        # -- from a usability perspective.
        self.label: str = label

        # -- We do not hard code the base class. We do expect all base classes to
        # -- ultimately inherit from xstack.Component, but by allowing you to specify
        # -- your own base class that inherits from the xstack.Component means you
        # -- can provide a more tailored expoerience.
        self.component_base_class = component_base_class

        # -- This is where our components should be sourced from
        self.component_paths: typing.List = component_paths or list()

        # -- The build hierarchy is held as a list of root components;
        # -- each component owns its own children, so the full tree is
        # -- reachable by walking from each root.
        self.root_components = list()

        # -- Declare our signals. These are useful for other classes
        # -- to bind into
        self.component_added = signalling.Signal()
        self.component_removed = signalling.Signal()
        self.hierarchy_changed = signalling.Signal()
        self.changed = signalling.Signal()

        self.build_started = signalling.Signal()
        self.build_progressed = signalling.Signal()
        self.build_completed = signalling.Signal()
        self.build_finished = signalling.Signal()
        self.build_failed = signalling.Signal()
        self.component_reporting = signalling.Signal()

        # -- The build_below components of the builds currently running, outermost
        # -- first. Anything in this list means we are inside a build.
        self._active_builds: typing.List = list()

        # -- The first failure reported by a nested build, so the outer build
        # -- can report the component that actually failed
        self._nested_failure = None

    @functools.cached_property
    def component_library(self) -> factories.Factory:
        """
        This will return a factory class giving access to all the available components.

        Note that it is a cached property, as we do not want to re-instance the factory
        each time it is called.
        """

        # -- Get a copy of our component path list
        paths = self.component_paths[:]

        # -- Add in any paths given to us by our environment
        paths.extend(
            os.environ.get(constants.COMPONENT_PATHS_ENVVAR, "").split(",")
        )

        # -- Remove any null entries
        paths = [
            p
            for p in paths
            if p
        ]

        # -- Instance the factory
        lib = factories.Factory(
            abstract=self.component_base_class,
            paths=paths,
            plugin_identifier="identifier",
        )

        return lib

    def add_component(
            self,
            component_type: str,
            label: str,
            inputs: typing.Dict = None,
            options: typing.Dict = None,
            parent: Component = None,
            child_index=None,
            force_uuid: str = None,
            suppress_events: bool = False,
    ) -> typing.Optional[Component]:
        """
        This will add a component of the given component type to the stack with the given
        label.

        Any inputs or options passed will have those values set at the time the
        component is added. Any that the component does not declare are skipped
        with a warning.

        If a parent uuid is given it will be assigned as a child of that component in
        the build order. If one is not given then it will be added to the end of the
        builder order list.

        if a forced uuid is given then the component will be assigned that uuid at time
        of initialisation rather than one being generated. This is typically only used
        when loading from pre-defined data.

        None is returned if the component type is not available or fails to
        initialise.
        """
        # -- Check we can access this component type
        if component_type not in self.component_library.identifiers():
            log.warning(f"{component_type} is not recognised")
            return None

        # -- We're instancing a class which comes from third party code. Because of
        # -- this, we wrap it in a broad exception test
        # noinspection PyBroadException
        try:
            component_instance: Component = self.component_library.request(
                component_type,
            )(
                label=label,
                stack=self,
                uuid_=force_uuid,
            )

        except Exception:
            log.exception(f"Failed to initialise component:  {component_type}")
            return None

        return self._add_component_instance(
            component_instance,
            inputs=inputs,
            options=options,
            parent=parent,
            child_index=child_index,
            suppress_events=suppress_events,
        )

    def _add_component_instance(
            self,
            component_instance: Component,
            inputs: typing.Dict = None,
            options: typing.Dict = None,
            parent: Component = None,
            child_index=None,
            suppress_events: bool = False,
    ) -> Component:
        """
        Applies the given inputs and options to an instanced component and adds it
        into the hierarchy of the stack.
        """
        component_type = component_instance.identifier

        # -- If we're given a parent, inherit any attributes that are flagged
        # -- as expecting inheritance.
        if parent:
            for option in component_instance.options():
                if not option.should_inherit():
                    continue
                parent_option = parent.option(option.name())
                if parent_option:
                    option.set(parent_option.get())

            for input_ in component_instance.inputs():
                if not input_.should_inherit():
                    continue
                parent_input = parent.input(input_.name())
                if parent_input:
                    input_.set(parent_input.get())

        # -- Set any option values we were given
        for option_name, value in (options or dict()).items():
            option = component_instance.option(option_name)

            if not option:
                log.warning(
                    f"{component_instance.label()} ({component_type}) has no option "
                    f"called '{option_name}', so its value has been dropped"
                )
                continue

            option.set(value)

        # -- Set any input values we were given
        for input_name, value in (inputs or dict()).items():
            input_ = component_instance.input(input_name)

            if not input_:
                log.warning(
                    f"{component_instance.label()} ({component_type}) has no input "
                    f"called '{input_name}', so its value has been dropped"
                )
                continue

            input_.set(value)

        # -- Whenever we have value changes, ensure we save the result
        component_instance.changed.connect(self.changed.emit)
        component_instance.set_parent(parent, child_index=child_index)

        # -- Call the enter stack feature
        if not suppress_events:
            component_instance.on_enter_stack()

        # -- Emit the fact that we have added the component and the
        # -- state has changed
        self.component_added.emit(component_instance)
        self.changed.emit()

        return component_instance

    def remove_component(self, component: Component) -> bool:
        """
        This will remove the given component, and recursively all of its
        descendants, from the stack. Each removed component receives an
        ``on_removed_from_stack`` callback and the stack emits a
        ``component_removed`` signal per component.
        """
        # -- Snapshot the children list before recursing — remove_component
        # -- mutates parent.children, which would shift indices mid-iteration.
        for child in list(component.children):
            self.remove_component(child)

        component.set_parent(None)
        self.root_components.remove(component)

        # noinspection PyBroadException
        try:
            component.on_removed_from_stack()
        except Exception:
            log.exception(f"on_removed_from_stack failed for {component.label()}")

        self.component_removed.emit()
        self.changed.emit()

        return True

    def serialise(self) -> typing.Dict:
        """
        This will serialise the stack down to a json format from which it can later
        be deserialised.

        :return: dict
        """
        return dict(
            label=self.label,
            tree=[
                root.serialise()
                for root in self.root_components
            ],
            format="galaxy"
        )

    def deserialize(self, data: typing.Dict, clear: bool = True):
        """
        This will take in a dictionary (of the format provided by the serialise
        method. The class will then be populated by all the data in that dictionary.

        Args:
            data: The dictionary of data to read the component list from
            clear: If True (default), any existing components are removed
                before deserialising. Pass False to append the loaded tree
                to the existing components.

        Note:
            This method uses the American spelling for historical
            reasons; the equivalent British-spelling alias
            :meth:`deserialise` is available and fully equivalent.
            Subclasses that need to extend the behaviour should
            override ``deserialize`` (the canonical implementation);
            both names will route through to the override.

        :return:
        """
        if clear:
            self.clear()

        # -- Ensure any legacy data format is converted
        # -- to the latest data format
        data = compat.to_latest(data)
        self.label = data.get("label", "stack")

        self._add_child_components(parent=None, child_list=data.get("tree", []))

    def deserialise(self, data: typing.Dict, clear: bool = True):
        """
        British-spelling alias for :meth:`deserialize`. Both methods
        are fully equivalent — pick whichever matches your codebase's
        convention. This alias routes through to ``deserialize`` so
        subclass overrides on the canonical name continue to work.
        """
        return self.deserialize(data, clear=clear)

    def _add_child_components(self, parent, child_list, regenerate_uuids=False):
        for child_data in child_list:
            self._add_component_from_data(
                child_data,
                parent=parent,
                regenerate_uuids=regenerate_uuids,
            )

    def _add_component_from_data(self, data: typing.Dict, parent, regenerate_uuids=False) -> Component:
        """
        Adds a component, and all its children, from serialised data.

        Data saved by an older version of the component is migrated first. If the
        component type is not available (or fails to initialise) a placeholder of
        missing_component_class is added instead, which keeps the data so that
        nothing is lost when the stack is next serialised.
        """
        component_type = data["component_type"]
        force_uuid = None if regenerate_uuids else data.get("uuid")

        component_class = None
        if component_type in self.component_library.identifiers():
            component_class = self.component_library.request(component_type)

        # -- Data saved before components were versioned counts as version 1
        stored_version = data.get("version", 1)

        if component_class and stored_version < component_class.version:

            # noinspection PyBroadException
            try:
                data = component_class.migrate(copy.deepcopy(data), stored_version)

            except Exception:
                log.exception(
                    f"Failed to migrate {data['label']} ({component_type}) from version "
                    f"{stored_version} to {component_class.version}"
                )
                component_class = None

        component = None

        if component_class:
            component = self.add_component(
                component_type,
                data["label"],
                inputs=data.get("inputs"),
                options=data.get("options"),
                force_uuid=force_uuid,
                suppress_events=True,
                parent=parent,
            )

        if not component:
            log.warning(
                f"The component type '{component_type}' could not be loaded, so "
                f"{data['label']} has been loaded as a placeholder. It keeps its data "
                f"but cannot be built."
            )
            component = self._add_component_instance(
                self.missing_component_class(
                    label=data["label"],
                    stack=self,
                    uuid_=force_uuid,
                    missing_identifier=component_type,
                    data=data,
                ),
                parent=parent,
                suppress_events=True,
            )

        # -- If the component was marked as disabled, then we disable it
        # -- now
        if not data.get("enabled", True):
            component.set_enabled(False)

        # -- Let the component restore any additional data before its
        # -- children are added, as they may rely on it
        component.deserialise_additional_data(data.get("additional_data"))

        # -- Create any children
        self._add_child_components(
            component,
            data.get("children", []),
            regenerate_uuids=regenerate_uuids,
        )

        return component

    def import_subtree_under(self, parent: "Component|None", filepath: str) -> None:
        """
        Load a serialised subtree from a JSON file and add the root
        components in that file as children of the given parent.

        Accepts files produced by both ``Component.save_settings()``
        (single-component shape) and ``Stack.save()`` (full-stack shape
        with a ``tree`` key). In the latter case, every root component
        in the file becomes a child of ``parent``.

        All component UUIDs are regenerated to avoid collisions with
        existing components in this stack. Labels are preserved, so any
        internal cross-references (which are label-based) continue to
        work after import. If a loaded component has a label that
        already exists in this stack, a warning is logged — address
        resolution will pick the first matching label, which may not be
        the intended one.

        :param parent: The Component to attach the loaded subtree to,
            or None to add the loaded components as root components.
        :param filepath: Absolute path to the JSON file.
        """
        if not filepath or not os.path.exists(filepath):
            log.warning(f"{filepath} does not exist")
            return

        with open(filepath, "r") as f:
            data = json.load(f)

        # -- Files saved via Component.save_settings() are a single
        # -- component dict; files saved via Stack.save() are a stack
        # -- dict with a "tree" key (or legacy "build_order"). Only run
        # -- the compat upgrader on stack-format data — single-component
        # -- dicts have no versioned format to raise.
        if "tree" in data or "build_order" in data:
            data = compat.to_latest(data)

        if "tree" in data:
            roots = data["tree"]
        else:
            roots = [data]

        # -- Warn about any label collisions before adding the new
        # -- components, since address resolution is label-based.
        existing_labels = {
            component.label()
            for component in self.components()
        }
        incoming_labels = self._collect_labels(roots)
        collisions = existing_labels & incoming_labels
        if collisions:
            log.warning(
                f"xstack.import_subtree_under: label collision(s) with existing "
                f"components: {sorted(collisions)}. Address resolution may be "
                f"ambiguous; consider renaming."
            )

        self._add_child_components(
            parent=parent,
            child_list=roots,
            regenerate_uuids=True,
        )

        self.hierarchy_changed.emit()

    @classmethod
    def _collect_labels(cls, child_list: typing.List) -> set:
        """
        Walks a serialised child list and returns the set of every
        label present in the tree.
        """
        labels = set()
        for child_data in child_list:
            labels.add(child_data["label"])
            labels.update(cls._collect_labels(child_data.get("children", [])))
        return labels

    def save(self, filepath, additional_data=None):
        """
        Saves the serialised data to a filepath, including any additional
        data.
        """
        if not filepath:
            log.warning("No filepath given to save to")
            return

        # -- Ensure we're fully serialised
        data = self.serialise()
        data["additional_data"] = additional_data

        with open(filepath, 'w') as f:
            json.dump(
                data,
                f,
                sort_keys=False,
                indent=4,
            )

    def clear(self):
        """
        Removes every component from the stack, firing
        ``component_removed`` and the component's
        ``on_removed_from_stack`` callback for each one — symmetric
        with :meth:`remove_component` so listeners and plugins see a
        consistent teardown.
        """
        # -- Snapshot the component list in build order before we
        # -- start mutating anything. We need descendants too, not
        # -- just root_components.
        components = self.components()

        for component in components:
            # noinspection PyBroadException
            try:
                component.on_removed_from_stack()
            except Exception:
                log.exception(f"on_removed_from_stack failed for {component.label()}")
            self.component_removed.emit()

        self.root_components = []
        self.changed.emit()

    @classmethod
    def open(
            cls,
            data: typing.Union[str, typing.Dict],
            component_paths: typing.Optional[typing.List] = None,
    ) -> "Stack":
        """
        Loads a Stack from either a JSON file path or an in-memory
        dict produced by :meth:`serialise`.

        :param data: Either a filepath to a JSON file, or the parsed
            dict directly.
        :param component_paths: Optional list of paths to add to the
            new stack's component library on construction.
        :raises FileNotFoundError: If ``data`` is a string but is
            empty or refers to a missing file.
        """
        if isinstance(data, str):
            if not data:
                raise FileNotFoundError(
                    "Stack.open requires a non-empty filepath or a dict."
                )

            if not os.path.exists(data):
                raise FileNotFoundError(f"Stack file not found: {data}")

            with open(data, "r") as f:
                data = json.load(f)

        stack = cls(
            label=data["label"],
            component_paths=component_paths or list(),
        )

        # -- Deserialise into the freshly-constructed stack. ``deserialize``
        # -- clears by default, but the stack has nothing to clear here.
        stack.deserialize(data)

        return stack

    def components(self, from_component=None, of_type=None):
        """
        Returns a list of all components used in the active stack. This is always
        returned in build order.
        """
        # -- Declare our list of components
        all_components = []

        # -- This function will cycle children (in order) and add those too
        def process_children(sub_component):
            for child in sub_component.children:
                all_components.append(child)
                process_children(child)

        start_points = [from_component] if from_component else self.root_components
        for component in start_points:
            all_components.append(component)
            process_children(component)

        if of_type:
            all_components = [
                component
                for component in all_components
                if component.identifier == of_type
            ]

        return all_components

    def get_component_by_uuid(self, uuid_: str) -> typing.Optional[Component]:
        """
        This will cycle the hierarchy and search it for a component
        with the given uuid.
        """
        for component in self.components():
            if component.uuid() == uuid_:
                return component

        return None

    def get_component_by_label(self, label, of_type=None) -> typing.Optional[Component]:
        """
        This will cycle the hierarchy and search it for a component
        with the given uuid.
        """
        for component in self.components():

            # -- If we're specifically looking for a particular
            # -- type then ignore anything which is not of that
            # -- type.
            if of_type and not component.identifier == of_type:
                continue

            if component.label() == label:
                return component

        return None

    def get_component_by_type(self, of_type) -> typing.Optional[Component]:
        """
        This will cycle the hierarchy and search it for a component
        with the given uuid.
        """
        for component in self.components():

            # -- If we're specifically looking for a particular
            # -- type then ignore anything which is not of that
            # -- type.
            if of_type == component.identifier:
                return component
        return None

    def _get_components_to_build(
            self,
            build_up_to: Component = None,
            build_only: Component = None,
            build_below: Component = None,
    ):
        # -- Pick the candidate set: the subtree below a given
        # -- component (build_below), or the whole stack otherwise.
        # -- The filter loop below runs the same way for both so
        # -- ``is_enabled`` / ``build_up_to`` / ``build_only`` are
        # -- honoured consistently regardless of entry point.
        if build_below:
            candidates = self.components(from_component=build_below)
        else:
            candidates = self.components()

        components = []
        for component in candidates:

            # -- A disabled component also disables all of its children
            if not self._is_enabled_in_hierarchy(component):
                continue

            if build_only and component != build_only:
                continue

            # -- This is where we need to perform the build.
            components.append(component)

            # -- End of the build
            if build_up_to and component == build_up_to:
                break
        return components

    @staticmethod
    def _is_enabled_in_hierarchy(component: Component) -> bool:
        """
        Returns True if the component and all of its ancestors are enabled
        """
        while component:
            if not component.is_enabled():
                return False
            component = component.parent
        return True

    def is_building(self) -> bool:
        """
        Returns True whilst a build (or validation) of this stack is running
        """
        return bool(self._active_builds)

    def build(
            self,
            build_up_to: Component = None,
            build_only: Component = None,
            build_below: Component = None,
            validate_only: bool = False
    ) -> bool:
        """
        This is the main function for building/executing the stack. You can choose to build
        up to a certain point in the build hierarchy or choose to build only a
        specific component.

        If neither are specified then all components will be built within the defined
        build order.

        A build started from within a component's run is a nested build. It only
        resets the status of the components it builds, emits no build signals, and
        is refused if it would build something that is already being built (such
        as two execution blocks which run each other).
        """
        nested = self.is_building()

        if nested and build_below in self._active_builds:
            target = build_below.label() if build_below else "The stack"
            log.error(
                f"{target} is already being built, so it cannot be built again "
                f"from within its own build. Check for components which run each "
                f"other's builds."
            )
            self._nested_failure = None
            return False

        self._active_builds.append(build_below)

        try:
            return self._build(
                build_up_to=build_up_to,
                build_only=build_only,
                build_below=build_below,
                validate_only=validate_only,
                nested=nested,
            )

        finally:
            self._active_builds.pop()

    def _build(self, build_up_to, build_only, build_below, validate_only, nested) -> bool:
        """
        Performs the build for the build method, which manages nesting
        """
        if not nested:
            self._nested_failure = None
            self.build_started.emit()

        components_to_build = self._get_components_to_build(
            build_up_to=build_up_to,
            build_only=build_only,
            build_below=build_below,
        )

        # -- Before doing any thing, ensure we have set every component
        # -- to not executed. A nested build leaves the status of the outer
        # -- build's components alone.
        for component in components_to_build if nested else self.components():
            component.set_status(
                Status.NotExecuted,
            )

        overall_build_start = time.time()

        # -- The first component to fail, and why
        failure = None

        # -- Cycle the build order. Note that we are not building at this point,
        # -- we are doing a full pass over all the components and checking they
        # -- are valid. If there are invalid components, we still continue, but
        # -- we log the fact and set the status.
        for component in components_to_build:

            # -- We're executing third party code at this point, so we cannot
            # -- gaurantee the quality of execution. Therefore we wrap it in
            # -- a try, to ensure a failure in the third party code does not
            # -- cause a failure at the stackx level
            # -- The validate and build lines below are the build report rather
            # -- than diagnostics, so they are printed as they are. A log record
            # -- only prefixes its first line, which breaks the report's columns.
            # noinspection PyBroadException
            try:
                self.component_reporting.emit(component, "validate")
                print(f"About to Validate : {component.label()}")

                if not component.is_valid():
                    component.set_status(
                        Status.Invalid,
                    )

                    reason = f"{component.label()} FAILED its is_valid test"
                    log.warning(reason)
                    failure = failure or (component, reason)

                for input_ in component.inputs():
                    if input_.requires_validation() and not input_.validate():
                        reason = f"{input_.name()} for {component.label()} is not set"
                        log.warning(reason)
                        failure = failure or (component, reason)

                        component.set_status(Status.Invalid)

            except Exception:
                log.exception(f"{component.label()} failed during validation check")
                component.set_status(
                    Status.Failed,
                )
                failure = failure or (component, traceback.format_exc())

        if failure:
            log.warning("Validation failed - please see output for details")
            return self._finish_build(False, nested, failure=failure)

        # -- If we only wanted to perform validation, we can exit at this point
        if validate_only:
            return self._finish_build(True, nested, validate_only=True)

        # -- Run the pre-build events
        self.run_events(components_to_build, "on_build_started")

        # -- We now re-cycle over the build order but this time we will trigger the build
        for idx, component in enumerate(components_to_build):

            # -- Emit a progression signal
            if not nested:
                percentage = (float(idx) / len(components_to_build)) * 100
                self.build_progressed.emit(percentage)

            start_time = time.time()

            # -- Any nested build this component runs will record its failure here
            self._nested_failure = None

            # -- Just as during the validation, we're executing third party code, so
            # -- we wrap this process in a broad exception
            # noinspection PyBroadException
            try:
                self.component_reporting.emit(component, "build")
                print(f"About to Build : {component.label()}")
                component.describe()
                result = component.wrapped_run()
                component.describe_outputs()
                print(
                    f"Component Build Status : {component.status()} "
                    f"({time.time() - start_time:.3f}s)"
                )

            except Exception:
                log.exception("Build failed")
                component.set_status(Status.Failed)
                failure = (component, traceback.format_exc())
                result = False

            if not result:

                # -- Where the component failed because a build it ran failed,
                # -- report the component which actually failed
                failure = failure or self._nested_failure or (component, component.last_error())

                self.run_events(components_to_build, "on_build_finished", False)
                return self._finish_build(False, nested, failure=failure)

        # -- Emit our completion
        self.run_events(components_to_build, "on_build_finished", True)
        print(f"Build Succeeded. ({time.time() - overall_build_start:.3f}s)")

        return self._finish_build(True, nested)

    def _finish_build(self, successful: bool, nested: bool, failure=None, validate_only=False) -> bool:
        """
        Emits the signals for the end of a build and returns whether it was
        successful. A nested build emits nothing, but records its failure so
        the outer build can report it.
        """
        if nested:
            if not successful:
                self._nested_failure = failure
            return successful

        if successful and not validate_only:
            self.build_progressed.emit(100)
            self.build_completed.emit()

        if not successful:
            component, details = failure or (None, "")
            self.build_failed.emit(component, details)

        self.build_finished.emit(successful)
        return successful

    def run_events(self, components, event_name, *args, **kwargs):
        for component in components:
            # noinspection PyBroadException
            try:
                func_ = getattr(component, event_name)
                func_(*args, **kwargs)

            except Exception:
                log.exception(f"{component.label()} failed during {event_name}")

    # ----------------------------------------------------------------------------------
    def resolve_attribute(self, attribute_address):
        return address.get_attribute(
            attribute_address,
            stack=self,
        )

    def replace_component(self, component: "xstack.Component", new_component_type: str):
        """
        This will replace the given component with a new component of the given
        component type.

        Where options or inputs match the data will be carried over. All children
        will also be carried over. This includes the stored data of a
        MissingComponent, so switching one to an available type keeps its values.
        """
        component_parent = component.parent
        component_child_index = component.child_index()

        new_component = self.add_component(
            component_type=new_component_type,
            label=component.label(),
            parent=None,
        )
        new_component.set_parent(component_parent, component_child_index)

        if isinstance(component, MissingComponent):
            stored_data = component.serialise()
            option_values = stored_data.get("options") or dict()
            input_values = stored_data.get("inputs") or dict()

        else:
            option_values = {
                option.name(): option.get(resolved=False)
                for option in component.options()
            }
            input_values = {
                input_.name(): input_.get(resolved=False)
                for input_ in component.inputs()
            }

        # -- Propogate any matching option data
        for name, value in option_values.items():
            if new_component.option(name):
                new_component.option(name).set(value)

        # -- Propogate any matching inputs
        for name, value in input_values.items():
            if new_component.input(name):
                new_component.input(name).set(value)

        # -- Make all the children of the component become
        # -- children of the new component instead
        indices = dict()
        for child in component.children[:]:
            indices[child] = child.child_index()

        for child, child_index in indices.items():
            child.set_parent(new_component, child_index=child_index)

        # -- Now we can remove the component
        self.remove_component(component)
        self.hierarchy_changed.emit()

        return new_component
