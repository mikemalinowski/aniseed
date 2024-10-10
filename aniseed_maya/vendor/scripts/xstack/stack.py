import os
import json
import typing
import functools
import traceback

from . import constants
from . import address

from .constants import Status
from .component import Component
from .signals import Signal

from .vendor import abstract_factories


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

        # -- These are where we store a mapping of uuid's to compnents. The build
        # -- order is then a list, where each element is a dict containing the uuid
        # -- and a list of children
        self._components = dict()
        self._build_order = list()

        # -- Declare our signals. These are useful for other classes
        # -- to bind into
        self.component_added = Signal()
        self.component_removed = Signal()
        self.build_order_changed = Signal()
        self.changed = Signal()

        self.build_started = Signal()
        self.build_completed = Signal()

    # ----------------------------------------------------------------------------------
    def serialise(self) -> typing.Dict:
        """
        This will serialise the stack down to a json format from which it can later
        be deserialised.

        :return: dict
        """
        data = dict(
            label=self.label,
            components=dict(),
            build_order=self._build_order,
        )

        for uuid, component in self._components.items():
            data["components"][component.uuid()] = component.serialise()

        return data

    # ----------------------------------------------------------------------------------
    def deserialize(self, data: typing.Dict):
        """
        This will take in a dictionary (of the format provided by the serialise
        method. The class will then be populated by all the data in that dictionary.

        Args:
            data: The dictionary of data to read the component list from

        :return:
        """
        self.label = data.get("label", "stack")

        # -- Add in the components
        for uuid, component_data in data.get("components", dict()).items():

            # -- Pull out the requirement and option data so we can format it in
            # -- a way we can pass through
            requirements = dict()
            options = dict()

            for requirement_data in component_data["requirements"]:
                requirements[requirement_data["name"]] = requirement_data["value"]

            for option_data in component_data["options"]:
                options[option_data["name"]] = option_data["value"]

            # -- Ad the component. Note that we specifically set the _serialise to
            # -- False during this call, because we do not want to change the serialised
            # -- data whilst initialising.
            new_component = self.add_component(
                component_data["component_type"],
                component_data["label"],
                requirements=requirements,
                options=options,
                force_uuid=uuid,
                forced_version=component_data.get("forced_version", None),
                _serialise=False,
            )

            if not component_data.get("enabled", True):
                new_component.set_enabled(False)

        # -- Pull out any stored build order data
        self._build_order = data.get("build_order", list())
        self.serialise()

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
        This is the main function for building/executing the stack. You can choose to build
        up to a certain point in the build hierarchy or choose to build only a
        specific component.

        If neither are specified then all components will be built within the defined
        build order.
        """

        if isinstance(build_up_to, Component):
            build_up_to = build_up_to.uuid()

        if isinstance(build_below, Component):
            build_below = build_below.uuid()

        if build_only:

            if not isinstance(build_only, list):
                build_only = [build_only]

            for idx, item in enumerate(build_only):
                if isinstance(item, Component):
                    build_only[idx] = item.uuid()

        self.build_started.emit()

        # -- Before doing any thing, ensure we have set every component
        # -- to not executed.
        for component in self.components():
            component.set_status(
                Status.NotExecuted,
            )

        # -- Our build order is fundamentally hierarchical. However, we can process
        # -- that down to a flat execution list.
        build_order = self._flattened_build_order(
            build_up_to,
            build_only,
            build_below,
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
        for uuid_ in build_order:

            # -- Get the component via the uuid
            component_instance: Component = self._components.get(uuid_)

            # -- We're executing third party code at this point, so we cannot
            # -- gaurantee the quality of execution. Therefore we wrap it in
            # -- a try, to ensure a failure in the third party code does not
            # -- cause a failure at the stackx level
            try:

                print("-" * 100)
                print(f"About to Validate : {component_instance.label()} ")

                if not component_instance.is_valid():
                    component_instance.set_status(
                        Status.Invalid,
                    )

                    print(f"    {component_instance.label()} FAILED its is_valid test")
                    invalid_result = True

                for requirement in component_instance.requirements():
                    if requirement.requires_validation() and not requirement.validate():
                        print(f"    {requirement.name()} for {component_instance.label()} is not set")
                        invalid_result = True

                        component_instance.set_status(
                            Status.Invalid,
                        )

            except:
                print(f"{component_instance.label()} failed during validation check")
                print(traceback.print_exc())
                component_instance.set_status(
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

        # -- We now re-cycle over the build order but this time we will trigger the build
        for uuid_ in build_order:

            # -- Get the component for the given uuid
            component_instance = self._components.get(uuid_)

            if not component_instance:
                print(f"Could not find component with id : {uuid_}")
                return False

            # -- Just as during the validation, we're executing third party code, so
            # -- we wrap this process in a broad exception
            # noinspection PyBroadException
            try:
                print("-" * 100)
                print(f"About to Build : {component_instance.label()} ")
                component_instance.describe()
                result = component_instance.wrapped_run()
                component_instance.describe_outputs()
                print(f"Component Build Status : {component_instance.status()}")

            except:

                print("Build failed. Please see the script editor for a traceback.")
                print(traceback.print_exc())
                return False

            if not result:
                return False

        # -- Emit our completion
        print("Build Succeeded.")
        self.build_completed.emit()

        return True

    # ----------------------------------------------------------------------------------
    def add_component(
            self,
            component_type: str,
            label: str,
            requirements: typing.Dict = None,
            options: typing.Dict = None,
            forced_version: int or None = None,
            parent: Component = None,
            force_uuid: str = None,
            _serialise: bool = True,

    ) -> Component or None:
        """
        This will add a component of the given component type to the stack with the given
        label.

        Any requirements or options passed will have those values set at the time the
        component is added.

        If a parent uuid is given it will be assigned as a child of that component in
        the build order. If one is not given then it will be added to the end of the
        builder order list.

        if a forced uuid is given then the component will be assigned that uuid at time
        of initialisation rather than one being generated. This is typically only used
        when loading from pre-defined data.
        """

        # -- Check we can access this component type
        if component_type not in self.component_library.names():
            print(f"{component_type} is not recognised")
            return None

        # -- We're instancing a class which comes from third party code. Because of
        # -- this, we wrap it in a broad exception test
        # noinspection PyBroadException
        try:
            component_instance: Component = self.component_library.get(
                component_type,
                version=forced_version,
            )(
                label=label,
                stack=self,
                uuid_=force_uuid,
            )

        except:
            print(f"Failed to initialise component:  {component_type}")
            print(traceback.print_exc())
            return None

        if forced_version:
            component_instance.set_forced_version(forced_version)

        # -- If we're given a parent, inherit any attributes that are flagged
        # -- as expecting inheritence
        if parent:
            print("Testing attribute inheritence")
            for option in component_instance.options():
                if option.should_inherit() and parent.option(option.name()):
                    print("inheriting option")
                    option.set(parent.option(option.name()).get())

            for requirement in component_instance.requirements():
                if requirement.should_inherit() and parent.requirement(
                        requirement.name()):
                    print("inheriting requirement")
                    requirement.set(parent.requirement(requirement.name()).get())

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

        # -- Set any requirement values we were given
        for requirement_name, value in (requirements or dict()).items():
            try:
                component_instance.requirement(requirement_name).set(value)

            except AttributeError:
                print(
                    f"{requirement_name} does not exist as a "
                    f"requirement for {component_type}"
                )

        # -- Whenever we have value changes, ensure we save the result
        component_instance.changed.connect(self.serialise)

        # -- Store the component
        self._components[component_instance.uuid()] = component_instance

        # -- Set the build position as per the parent. Note that if the parent
        # -- is None, then this component will just be added to the end of the build
        # -- list
        self.set_build_position(
            component_instance,
            parent,
            _serialise=False,
        )

        # -- Call the enter stack feature
        component_instance.on_enter_stack()

        # -- Emit the fact that we have added the component and the
        # -- state has changed
        self.component_added.emit(component_instance)
        self.changed.emit()

        return component_instance

    # ----------------------------------------------------------------------------------
    def get_parent(self, component):

        def recursive_inner_(current_uuid, search_for_uuid, sub_data):
            for item in sub_data:
                if item["uuid"] == search_for_uuid:
                    return current_uuid

                result = recursive_inner_(item["uuid"], search_for_uuid,
                                          item["children"])

                if result:
                    return result

        parent_uuid = recursive_inner_(None, component.uuid(), self.build_order())

        if parent_uuid:
            return self.component(parent_uuid)

    # ----------------------------------------------------------------------------------
    def get_children(self, component):

        def recursive_inner_(current_uuid, search_for_uuid, sub_data):
            for item in sub_data:
                if item["uuid"] == search_for_uuid:
                    return [
                        self.component(c["uuid"])
                        for c in item["children"]
                    ]

                result = recursive_inner_(
                    item["uuid"],
                    search_for_uuid,
                    item["children"]
                )

                if result:
                    return result

        return recursive_inner_(None, component.uuid(), self.build_order())

    # ----------------------------------------------------------------------------------
    def get_index(self, component):

        def recursive_inner_(current_uuid, search_for_uuid, sub_data):
            for idx, item in enumerate(sub_data):
                if item["uuid"] == search_for_uuid:
                    return idx

                result = recursive_inner_(
                    item["uuid"],
                    search_for_uuid,
                    item["children"],
                )

                if result is not None:
                    return result

        return recursive_inner_(
            None,
            component.uuid(),
            self.build_order(),
        )

    # ----------------------------------------------------------------------------------
    def switch_component_version(self, component, version):
        """
        Instances a new component of the desired version in place of the
        previous one.
        """
        requirements = dict()
        options = dict()


        for req in component.requirements():
            requirements[req.name()] = req.get()

        for option in component.options():
            options[option.name()] = option.get()

        parent = self.get_parent(component)
        placement_index = self.get_index(component)
        children = self.get_children(component)

        # -- Start by moving the children to the root so they do not
        # -- get removed with the component
        for child in children or list():
            self.set_build_position(
                child,
                parent=None,
            )

        self.remove_component(component)

        new_component = self.add_component(
            component_type=component.identifier,
            label=component.label(),
            requirements=requirements,
            options=options,
            forced_version=version,
            force_uuid=component.uuid(),
            # parent=parent,
        )

        self.set_build_position(
            new_component,
            parent=parent,
            index=placement_index,
        )

        for child in children or list():
            self.set_build_position(
                child,
                parent=new_component,
            )
        return None

    # ----------------------------------------------------------------------------------
    def set_build_position(
            self,
            component: Component,
            parent: Component = None,
            index: int = None,
            _serialise: bool = True
    ):
        """
        This sets where in the stack this component should be placed. You should specify
        a parent (if none is given then it will go to the end of the list).

        If an index is given then it will be added at that point in the parents child
        list.
        """

        # -- Start by removing the component from the build order
        removed_component_data = self._remove_from_build_order(
            component.uuid(),
        )

        # -- If we could not remove it, then the component must not be
        # -- added yet, so lets create a data set to add it
        if not removed_component_data:
            removed_component_data = {
                "uuid": component.uuid(),
                "label": component.label(),
                "children": [],
            }

        # -- Get the uuid of the parent if we were given one
        parent_uuid = parent.uuid() if parent else None

        # -- Inset the build order data into our build order
        # -- variable
        self._insert_build_order_data(
            removed_component_data,
            parent_uuid,
            index,
        )

        # -- Emit the fact that the builder order has changed
        self.build_order_changed.emit()
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def remove_component(self, component: Component) -> bool:
        """
        This will remove the given component from the stack and the build order.
        """
        # -- We're removing the component from the dictionary, but we're
        # -- also executing third-party code, so we wrap this process in
        # -- a broad exception
        try:
            uuid_ = component.uuid()

            if uuid_ in self._components:
                del self._components[uuid_]

            self._remove_from_build_order(
                uuid_,
            )

            # -- Ensure we clear any connection signals
            component.changed.disconnect()

        except (KeyError, Exception):
            print(f"Could not remove {component}")
            print(traceback.print_exc())
            return False

        # -- Call the removed feature
        component.on_removed_from_stack()

        self.component_removed.emit()
        self.changed.emit()

        return True

    # ----------------------------------------------------------------------------------
    def build_order(self) -> typing.List:
        """
        Returns the build order dictionary
        """
        return self._build_order

    # ----------------------------------------------------------------------------------
    def component(self, uuid_: str) -> Component or None:
        """
        This will return the component within the rig with the given uuid
        """
        return self._components.get(uuid_, None)

    # ----------------------------------------------------------------------------------
    def components(self, of_type=None) -> typing.List[Component]:
        """
        THis will return a list of all the components in the rig
        """
        results = list()

        for component in self._components.values():
            if of_type and component.identifier != of_type:
                continue

            results.append(component)

        return results

    # ----------------------------------------------------------------------------------
    def clear_components(self):
        self._components = dict()
        self._build_order = list()

        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def lookup_attribute(self, attribute_address):
        return address.get_attribute(
            attribute_address,
            stack=self,
        )

    # ----------------------------------------------------------------------------------
    @classmethod
    def load(cls, data: str or typing.Dict,
             component_paths: typing.List or None = None):
        """
        Given a filepath or a dictionary of data, this will populate the stack
        based on that data. Note that if its a filepath that is given the contents
        of that filepath are expected to be a dictionary of a structure that conforms
        to the serialise method.

        Args:
            data: This may be a dictionary or a json file

        :return:
        """
        if isinstance(data, str):
            with open(data, "r") as f:
                data = json.load(f)

        stack = cls(
            label=data["label"],
            component_paths=component_paths or list(),
        )

        # -- Clear the stack before we deserialise
        stack.clear_components()

        # -- Now we have the data in the right format, we can deserialise
        # -- from it
        stack.deserialize(data)

        return stack

    # ----------------------------------------------------------------------------------
    def save(self, filepath: str, additional_data: typing.Dict or None = None):
        """
        This will serialise the stack to a dictionary, including any additional data
        you may want to stored with it, and then saved to the given filepath
        """

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

    # ----------------------------------------------------------------------------------
    def _remove_from_build_order(self, uuid_: str) -> typing.Dict:
        """
        This will traverse all the build order data and remove the entry with the
        given uuid.

        It will return the removed data.
        """

        def recursive_inner_(identifier, sub_data):
            for item in sub_data:
                if item["uuid"] == identifier:
                    sub_data.remove(item)
                    return item

                result = recursive_inner_(identifier, item["children"])

                if result:
                    return result

        removed_data = recursive_inner_(uuid_, self.build_order())

        return removed_data

    # ----------------------------------------------------------------------------------
    def _get_build_order_dict(
            self,
            uuid_: str,
            sub_data: typing.List = None,
    ) -> typing.Dict or None:
        """
        The build order is a list containing dictionaries, where each dictionary is a
        description of the component (uuid, label and children).

        This method will return that dictionary description for the given uuid.

        Note, this is a recursive function, the sub_data is the point from which you
        want to search from. If None is provided then it will search from the top of
        the build order data.
        """
        if not uuid_:
            return None

        result = None

        if sub_data is None:
            sub_data = self.build_order()

        for item in sub_data:
            if item["uuid"] == uuid_:
                return item

        for item in sub_data:
            result = self._get_build_order_dict(uuid_, item["children"])

            if result:
                return result

        return result

    # ----------------------------------------------------------------------------------
    def _insert_build_order_data(
            self,
            data_to_insert: typing.Dict,
            parent_uuid: str,
            index: int = None,
    ):
        """
        Private function to inject the given data into the build order structure
        """
        items_build_dict = self._get_build_order_dict(uuid_=parent_uuid)

        if not items_build_dict or not parent_uuid:
            self._build_order.append(data_to_insert)
            return

        if items_build_dict is not None:

            if index is None:
                index = len(items_build_dict["children"])

            items_build_dict["children"].insert(index, data_to_insert)

    # ----------------------------------------------------------------------------------
    def _flattened_build_order(
            self,
            build_up_to: str = None,
            build_only: str = None,
            build_below: str = None,
    ) -> typing.List[str]:
        """
        The build order is hierarchical which makes sense from a user experience
        perspective, but we ultimately will execute it in a sequential list. This
        function flattens the hierarchy into a one dimensional build order where the
        entries in the list are the uuid's for the components.
        """
        build_list = list()

        def inner_(sub_data):
            for item_ in sub_data:
                if self.component(item_["uuid"]).is_enabled():
                    build_list.append(item_["uuid"])
                    inner_(item_["children"])

        if build_below:
            if self.component(build_below).is_enabled():
                build_list.append(build_below)
                inner_(
                    self._get_build_order_dict(
                        build_below,
                    )["children"],
                )

        else:
            inner_(self.build_order())

        if build_up_to:
            _build_list = []

            for item in build_list:
                _build_list.append(item)
                if item == build_up_to:
                    return _build_list

        if build_only:
            print(f"Build only value : {build_only}")
            if not isinstance(build_only, list):
                build_only = [build_only]

            return [
                item
                for item in build_list
                if item in build_only
            ]

        return build_list

    # --------------------------------------------------------------------------------------
    @functools.cached_property
    def component_library(self) -> abstract_factories.AbstractTypeFactory:
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
        lib = abstract_factories.AbstractTypeFactory(
            abstract=self.component_base_class,
            paths=paths,
            name_key="identifier",
            version_key="version",
            unique_items_only=True,
        )

        return lib
