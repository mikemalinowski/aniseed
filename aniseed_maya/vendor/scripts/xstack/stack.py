import os
import json
import typing
import functools
import traceback
import factories
import signalling

from . import constants
from . import compat
from . import address
from .constants import Status
from .component import Component


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

    builder_order_changed(): Emitted when an item is moved in the order of execution

    changed(): Emitted whenever a component is added or removed or the build order
        is changed in any way.
    """
    status = constants.Status

    # ----------------------------------------------------------------------------------
    def __init__(
            self,
            label: str = "",
            component_paths: typing.List or None = None,
            component_base_class=Component
    ):
        super(Stack, self).__init__()

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

        # -- Components is a dictionary where the key is a uuid and the
        # -- value is a component instance

        # -- The build hierarchy is a nested dictionary of uuid's
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
            supress_events: bool = False,
            _serialise: bool = True,

    ) -> Component or None:
        """
        This will add a component of the given component type to the stack with the given
        label.

        Any inputs or options passed will have those values set at the time the
        component is added.

        If a parent uuid is given it will be assigned as a child of that component in
        the build order. If one is not given then it will be added to the end of the
        builder order list.

        if a forced uuid is given then the component will be assigned that uuid at time
        of initialisation rather than one being generated. This is typically only used
        when loading from pre-defined data.
        """
        # -- Check we can access this component type
        if component_type not in self.component_library.identifiers():
            print(f"{component_type} is not recognised")
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

        except:
            print(f"Failed to initialise component:  {component_type}")
            print(traceback.print_exc())
            return None

        # -- If we're given a parent, inherit any attributes that are flagged
        # -- as expecting inheritence
        if parent:
            for option in component_instance.options():
                if option.should_inherit() and parent.option(option.name()):
                    option.set(parent.option(option.name()).get())

            for input_ in component_instance.inputs():
                if input_.should_inherit() and parent.input(input_.name()):
                    input_.set(parent.input(input_.name()).get())

        # -- Set any option values we were given
        for option_name, value in (options or dict()).items():
            try:
                component_instance.option(option_name).set(value)

            except AttributeError:
                traceback.print_exc()
                print(component_instance.options())
                print(
                    f"{option_name} does not exist as an "
                    f"option for {component_type}"
                )

        # -- Set any input values we were given
        for input_name, value in (inputs or dict()).items():
            try:
                component_instance.input(input_name).set(value)

            except AttributeError:
                print(
                    f"{input_name} does not exist as a "
                    f"input for {component_type}"
                )

        # -- Whenever we have value changes, ensure we save the result
        component_instance.changed.connect(self.changed.emit)
        component_instance.set_parent(parent, child_index=child_index)

        # -- Call the enter stack feature
        if not supress_events:
            component_instance.on_enter_stack()

        # -- Emit the fact that we have added the component and the
        # -- state has changed
        self.component_added.emit(component_instance)
        self.changed.emit()

        return component_instance

    def remove_component(self, component: Component) -> bool:
        """
        This will remove the given component from the stack and the build order.
        """
        # -- To remove we simply need to remove it from our hierarchy at
        # -- which point it will be garbage collected as soon as there
        # -- are no references.
        component.set_parent(None)
        self.root_components.remove(component)

        # -- Call the removed feature
        try:
            component.on_removed_from_stack()
        except:
            traceback.print_exc()

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

    def deserialize(self, data: typing.Dict):
        """
        This will take in a dictionary (of the format provided by the serialise
        method. The class will then be populated by all the data in that dictionary.

        Args:
            data: The dictionary of data to read the component list from

        :return:
        """
        # -- Ensure any legacy data format is converted
        # -- to the latest data format
        data = compat.to_latest(data)
        self.label = data.get("label", "stack")

        for root_data in data.get("tree", []):
            root_component = self.add_component(
                root_data["component_type"],
                root_data["label"],
                inputs=root_data["inputs"],
                options=root_data["options"],
                force_uuid=root_data["uuid"],
                parent=None,
                supress_events=True,
                _serialise=False,
            )
            if not root_data.get("enabled", True):
                root_component.set_enabled(False)
            self._add_child_components(parent=root_component, child_list=root_data["children"])

    def _add_child_components(self, parent, child_list):
        for child_data in child_list:
            created_component = self.add_component(
                child_data["component_type"],
                child_data["label"],
                inputs=child_data["inputs"],
                options=child_data["options"],
                force_uuid=child_data["uuid"],
                supress_events=True,
                _serialise=False,
                parent=parent,
            )
            # -- If the component was marked as disabled, then we disable it
            # -- now
            if not child_data.get("enabled", True):
                created_component.set_enabled(False)

            # -- Create any children
            self._add_child_components(created_component, child_data["children"])

    def save(self, filepath, additional_data=None):
        """
        Saves the serialised data to a filepath, including any additional
        data.
        """
        if not filepath:
            print("No filepath given to save to")
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
        Removes all reference to all components and clears out
        """
        self.root_components = []
        self.changed.emit()

    @classmethod
    def open(cls, data: str or typing.Dict, component_paths: typing.List or None = None):

        if isinstance(data, str):
            if not data or not os.path.exists(data):
                print("%s does not exist" % data)
                return

            with open(data, "r") as f:
                data = json.load(f)

        stack = cls(
            label=data["label"],
            component_paths=component_paths or list(),
        )

        # -- Clear the stack before we deserialise
        stack.clear()

        # -- Now we have the data in the right format, we can deserialise
        # -- from it
        stack.deserialize(data)

        return stack

    def components(self, from_component=None):
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

        return all_components

    def get_component_by_uuid(self, uuid_: str) -> Component or None:
        """
        This will cycle the hierarchy and search it for a component
        with the given uuid.
        """
        for component in self.components():
            if component.uuid() == uuid_:
                return component

        return None

    def get_component_by_label(self, label, of_type=None) -> Component or None:
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

    def _get_components_to_build(
            self,
            build_up_to: Component = None,
            build_only: Component = None,
            build_below: Component = None,):
        components = []

        if build_below:
            return self.components(from_component=build_below)

        for component in self.components():

            if not component.is_enabled():
                continue

            if build_only and component != build_only:
                continue

            # -- This is where we need to perform the build.
            components.append(component)

            # -- End of the build
            if build_up_to and component == build_up_to:
                break
        return components

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
        """
        self.build_started.emit()

        # -- Before doing any thing, ensure we have set every component
        # -- to not executed.
        for component in self.components():
            component.set_status(
                Status.NotExecuted,
            )

        components_to_build = self._get_components_to_build(
            build_up_to=build_up_to,
            build_only=build_only,
            build_below=build_below,
        )

        # -- Lets be positive and assume everything is ok until we're told
        # -- otherwise.
        invalid_result = False

        # -- Cycle the build order. Notice that we're not given the component
        # -- themselves but the uuid to retrieve the component. Note that we
        # -- are not building at this point, we are doing a full pass over all the
        # -- components and checking they are valid.
        # -- If there are invalid components, we still continue, but we log the
        # -- fact and set the status.
        for component in components_to_build:

            # -- We're executing third party code at this point, so we cannot
            # -- gaurantee the quality of execution. Therefore we wrap it in
            # -- a try, to ensure a failure in the third party code does not
            # -- cause a failure at the stackx level
            try:

                print("-" * 100)
                print(f"About to Validate : {component.label()} ")

                if not component.is_valid():
                    component.set_status(
                        Status.Invalid,
                    )

                    print(f"    {component.label()} FAILED its is_valid test")
                    invalid_result = True

                for input_ in component.inputs():
                    if input_.requires_validation() and not input_.validate():
                        print(f"    {input_.name()} for {component.label()} is not set")
                        invalid_result = True

                        component.set_status(Status.Invalid)

            except:
                print(f"{component.label()} failed during validation check")
                print(traceback.print_exc())
                component.set_status(
                    Status.Failed,
                )
                invalid_result = True

        if invalid_result:
            print("Validation failed - please see output for details")
            print("-" * 100)
            return False

        # -- If we only wanted to perform validation, we can exit at this point
        if validate_only:
            return not invalid_result

        # -- Run the pre-build events
        self.run_events(components_to_build, "on_build_started")

        # -- We now re-cycle over the build order but this time we will trigger the build
        for idx, component in enumerate(components_to_build):

            # -- Emit a progression signal
            percentage = (float(idx) / len(components_to_build)) * 100
            self.build_progressed.emit(percentage)

            # -- Just as during the validation, we're executing third party code, so
            # -- we wrap this process in a broad exception
            # noinspection PyBroadException
            try:
                print("-" * 100)
                print(f"About to Build : {component.label()} ")
                component.describe()
                result = component.wrapped_run()
                component.describe_outputs()
                print(f"Component Build Status : {component.status()}")

            except:

                print("Build failed. Please see the script editor for a traceback.")
                print(traceback.print_exc())
                self.run_events(components_to_build, "on_build_finished", False)
                return False

            if not result:
                self.run_events(components_to_build, "on_build_finished", False)
                return False

        # -- Emit our completion
        self.run_events(components_to_build, "on_build_finished", True)
        print("Build Succeeded.")
        self.build_progressed.emit(100)
        self.build_completed.emit()

        return True

    def run_events(self, components, event_name, *args, **kwargs):
        for component in components:
            try:
                func_ = getattr(component, event_name)
                func_(*args, **kwargs)

            except:
                print(f"{component.label()} failed during its pre build")
                print(traceback.print_exc())

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
        will also be carried over.
        """
        component_parent = component.parent
        component_child_index = component.child_index()

        new_component = self.add_component(
            component_type=new_component_type,
            label=component.label(),
            parent=None,
        )
        new_component.set_parent(component_parent, component_child_index)

        # -- Propogate any matching option data
        for option in component.options():
            if new_component.option(option.name()):
                new_component.option(option.name()).set(option.get(resolved=False))

        # -- Propogate any matching inputs
        for input_ in component.inputs():
            if new_component.input(input_.name()):
                new_component.input(input_.name()).set(input_.get(resolved=False))

        # -- Make all the children of the component become
        # -- children of the new component instead
        indices = dict()
        for child in component.children[:]:
            indices[child] = child.child_index()

        for child, child_index in indices.items():
            print("got child : %s" % child.label())
            child.set_parent(new_component, child_index=child_index)

        # -- Now we can remove the component
        self.remove_component(component)
        self.hierarchy_changed.emit()

        return new_component
