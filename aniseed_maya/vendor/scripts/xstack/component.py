import uuid
import json
import copy
import typing
import traceback
import signalling

from . import stack
from .attributes import Option
from .attributes import Input
from .attributes import Output
from .constants import Status


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class Component:
    """
    A component is a an item that can be added to the stack. Typically, a component
    will expose various options and inputs and then execute some code utilising
    those options and inputs.

    When implementing a component, you should subclass from this Component class and
    provide a unique identifier. Components are stored in a class factory thus the
    identifier is used to differentiate the different components.

    Key things you should re-implement when subclassing a component:

    All the functions you may re-implement are at the top of this class. Please
    do not alter/modify/re-implement any functionality below the warning line.
    """

    # -- Please provide a unique identifier
    identifier = ""

    # -- This should resolve to an absolute path to a png file. If none is provide
    # -- then a default icon will be given.
    # -- To prevent hard coding the absolute path, you can use this syntax if your
    # -- icon is in the same folder as your component .py:
    # -- icon = os.path.join(os.path.dirname(__file__), "my_icon_name.png")
    icon = ""

    # ----------------------------------------------------------------------------------
    # This MUST be re-implemented
    def run(self) -> bool:
        """
        This should be re-implemented in your component and should contain all the
        code which you want to trigger during the build.
        """
        return True

    # ----------------------------------------------------------------------------------
    # You may re-implement this
    def is_valid(self) -> bool:
        """
        You can use this to test the validation of the options and requirements.
        """
        return True

    # ----------------------------------------------------------------------------------
    # You may re-implement this
    def option_widget(self, option_name: str) -> "PySide6.QWidget":
        """
        This allows you to return a specific (or custom) QWidget to represent the
        given option in any ui's.

        This requires Qt, which is optional.

        For example, your code here might look like this:

        ```
        if option_name == "foobar":
            return qute.QLineEdit()
        ```

        If you do not want a specific option to be shown in the ui, you can do:

        if option_name == "foobar":
            return self.IGNORE_OPTION_FOR_UI
        """
        return None

    # ----------------------------------------------------------------------------------
    # You may re-implement this
    def input_widget(self, requirement_name: str) -> "PySide6.QWidget":
        """
        This allows you to return a specific (or custom) QWidget to represent the
        given requirement in any ui's.

        This requires Qt, which is optional.

        For example, your code here might look like this:

        ```
        if requirement_name == "foobar":
            return qute.QLineEdit()
        ```

        If you do not want a specific requirement to be shown in the ui, you can do:

        if requirement_name == "foobar":
            return self.IGNORE_OPTION_FOR_UI
        """
        return None

    # ----------------------------------------------------------------------------------
    def on_add_to_stack(self):
        """
        Triggered when the component is first added to the stack
        """
        return None

    # ----------------------------------------------------------------------------------
    def on_enter_stack(self):
        """
        This allows you to run any code when this is added to the stack

        :return:
        """
        return None

    # ----------------------------------------------------------------------------------
    def on_removed_from_stack(self):
        """
        This is triggered if this component is removed from the stack

        :return:
        """
        return None

    # ----------------------------------------------------------------------------------
    def on_build_finished(self, successful: bool) -> None:
        """
        This is run when the build is complete and will pass bool declaring whether the
        build was successful or not.

        Args:
             successful (bool): Whether the build was successful or not.
        """
        pass

    # ----------------------------------------------------------------------------------
    def on_build_started(self) -> None:
        """
        This is run immediately at the start of the build before any components have
        their run functions called.
        """
        pass

    # ----------------------------------------------------------------------------------
    def help(self):
        """
        This function should be used to integrate any help mechanism you want to utilise
        for your component.

        Examples could include opening a url to a help webpage. Or loading a video or
        other document.
        """
        return None

    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:
        return dict()

    # ---------------------------------------------------------------------------------#
    #                DO NOT RE-IMPLEMENT ANY FUNCTIONS BELOW THIS LINE                 #
    # ---------------------------------------------------------------------------------#

    # ----------------------------------------------------------------------------------
    def __init__(self, label: str, stack: "stack.Stack", uuid_: str or None = None):
        super(Component, self).__init__()

        self.stack: "stack.Stack" = stack

        self._label: str = label
        self._uuid: str = uuid_ or str(uuid.uuid4())
        self._inputs: typing.List[Input] = list()
        self._options: typing.List[Option] = list()
        self._outputs: typing.List[Output] = list()
        self._status: str = "not executed"
        self._enabled = True

        # -- Hierarchy attributes
        self.parent = None
        self.children = []

        # -- Declare our signals so that other mechanisms can tie into the events
        # -- of our component
        self.build_started = signalling.Signal()
        self.build_complete = signalling.Signal()
        self.changed = signalling.Signal()

    def set_parent(self, parent=None, child_index=None):

        # -- Ensure we're removed as a root component
        if self in self.stack.root_components:
            self.stack.root_components.remove(self)

        # -- Remove ourself from our current parent if we have
        # -- one
        if self.parent:
            self.parent.children.remove(self)

        self.parent = parent
        # -- If we're given a component to be a child of, then
        # -- we perform our reparenting otherwise we add ourselves
        # -- as a root component
        if isinstance(parent, Component):
            # -- Add ourself as a child of the component
            if child_index is not None:
                parent.children.insert(child_index, self)
            else:
                parent.children.append(self)
        else:
            if child_index is not None:
                self.stack.root_components.insert(child_index, self)
            else:
                self.stack.root_components.append(self)

    def child_index(self):
        if self.parent:
            return self.parent.children.index(self)
        else:
            return self.stack.root_components.index(self)

    # ----------------------------------------------------------------------------------
    def wrapped_run(self) -> bool:
        """
        This should NOT be re-implemented. This is used specifically by the Stack class
        to instigate your implement function whilst wrapped in the signal  and
        logging mechanisms.
        """
        self.build_started.emit()

        result = True

        try:
            self.run()
            self.set_status(Status.Success)

        except Exception:
            self.set_status(Status.Failed)
            traceback.print_exc()
            result = False

        self.build_complete.emit()

        return result

    # ----------------------------------------------------------------------------------
    def is_enabled(self):
        """
        This will return whether the component is flagged as enabled. Any component
        that is not enabled will not be executed.
        """

        return self._enabled

    # ----------------------------------------------------------------------------------
    def set_enabled(self, value):
        """
        Set the enabled state of the component. Any component that has this set to
        false will not be executed.

        A disabled component will also not execute any of its children.
        """
        self._enabled = value
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def status(self) -> str:
        """
        This will return the current status string for the component
        """
        if not self.is_enabled():
            return Status.Disabled

        return self._status

    # ----------------------------------------------------------------------------------
    def set_status(self, status: str):
        """
        This will set the status of this component. Generally you should leave the Stack
        class to call this.
        """
        self._status = status

    # ----------------------------------------------------------------------------------
    def uuid(self) -> str:
        """
        All component instances have a completely unique identifier - allowing the build
        process and the Stack to keep track of all component instances. This function will
        return this.
        """
        return self._uuid

    # ----------------------------------------------------------------------------------
    def label(self) -> str:
        """
        Returns the label for the component. The label generally has no bearing on the
        building of the component, but it allows for the user to keep track of what
        components are and their use cases.
        """
        return self._label

    # ----------------------------------------------------------------------------------
    def set_label(self, label: str):
        """
        Sets the label of the component. Note that this will trigger a change event
        """
        self._label = label
        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def suggested_label(self):
        return self.identifier

    # ----------------------------------------------------------------------------------
    def declare_input(
            self, name: str,
            value: typing.Any = None,
            description: str = "",
            validate=True,
            group=None,
            should_inherit=False,
            pre_expose=False,
            hidden=False,
    ):
        """
        This will add a requirement to the component, which will allow a user to
        set the requirement and allow for your inmplement function to query that
        value.

        Args:
            name (str): The name of the requirement.

            value (Any): The value of the requirement.

            description (str): The description of the requirement to be presented to
                the user.

            validate (bool): Whether or not the requirement should be validated prior
                to its component being executed.

            group (str): If given, this requirement will be grouped together in any
                ui's with requirements of the same group.

            should_inherit (bool): Whether or not the requirement should inherit
                its value from its parent when it is initialised.

            pre_expose (bool): Whether or not the requirement should be exposed. This
                is to help inform ui's as to whether the user should be presented
                with this requirement before the component is created.

            hidden (bool): Whether or not the requirement should be hidden.
        """
        input_ = Input(
            name=name,
            value=value,
            validate=validate,
            description=description,
            group=group,
            should_inherit=should_inherit,
            pre_expose=pre_expose,
            hidden=hidden,
            component=self,
        )

        self._inputs.append(input_)

        # -- Trickle the change event of this requirement to the component level
        input_.value_changed.connect(self.changed.emit)

    # ----------------------------------------------------------------------------------
    def declare_option(
            self,
            name: str,
            value: typing.Any,
            description: str = "",
            group=None,
            should_inherit=False,
            pre_expose=False,
            hidden=False,
    ):
        """
        This will add an option to the component, which will allow a user to
        set the option and allow for your inmplement function to query that
        value.

        Args:
            name (str): The name of the option.

            value (Any): The value of the option.

            description (str): The description of the option to be presented to
                the user.

            group (str): If given, this option will be grouped together in any
                ui's with options of the same group.

            should_inherit (bool): Whether or not the option should inherit
                its value from its parent when it is initialised.

            pre_expose (bool): Whether or not the option should be exposed. This
                is to help inform ui's as to whether the user should be presented
                with this option before the component is created.

            hidden (bool): Whether or not the option should be hidden.
        """
        option = Option(
            name=name,
            value=value,
            description=description,
            group=group,
            should_inherit=should_inherit,
            pre_expose=pre_expose,
            hidden=hidden,
            component=self,
        )

        self._options.append(option)

        # -- Trickle the change event of the option to the component level
        option.value_changed.connect(self.changed.emit)

    # ----------------------------------------------------------------------------------
    def declare_output(self, name: str, description: str = "", group=None, is_default=False):
        """
        An output is a guaranteed value that a component will fill in during its
        run, and can be looked up by other components.

        This mechanism allows for components to dynamically resolve values from
        other components rather than have them explicitely set
        """
        output = Output(
            name=name,
            description=description,
            component=self,
            is_default=is_default,
            group=group,
        )
        self._outputs.append(output)

    # ----------------------------------------------------------------------------------
    def default_output(self):
        """
        This will return the output that is marked as default. If one is not defined then
        None will be returned.
        """
        for output_plug in self._outputs:
            if output_plug.is_default():
                return output_plug
        return None

    # ----------------------------------------------------------------------------------
    def inputs(self) -> typing.List[Input]:
        """
        Returns a list of the inputs for this component
        """
        return self._inputs

    # ----------------------------------------------------------------------------------
    def input(self, name: str) -> Input or None:
        """
        Returns the Input object for the given requirement name
        """
        for input_ in self._inputs:
            if input_.name() == name:
                return input_

        return None

    # ----------------------------------------------------------------------------------
    def options(self) -> typing.List[Option]:
        """
        Returns a list of theoptions for this component
        """
        return self._options

    # ----------------------------------------------------------------------------------
    def option(self, name: str) -> Option or None:
        """
        Returns the Option object for the given option name
        """
        for option_ in self._options:
            if option_.name() == name:
                return option_

        return None

    # ----------------------------------------------------------------------------------
    def outputs(self) -> typing.List[Output]:
        """
        Returns a list of outputs for this component
        Returns:

        """
        return self._outputs

    # ----------------------------------------------------------------------------------
    def output(self, name: str) -> Output or None:
        """
        Returns the Option object for the given option name
        """
        for output_ in self._outputs:
            if output_.name() == name:
                return output_

        return None

    def remove_output(self, name: str) -> None:
        output_ = self.output(name)
        self._outputs.remove(output_)

    # ----------------------------------------------------------------------------------
    def describe(self):
        """
        This will print a nicely formatted output description of the component
        """
        print(f"Component Type : {self.identifier}")
        print(f"    Identifier : {self.uuid()}")
        print(f"    Options    :")

        value_limit = 200

        option_len = max(
            [
                len(option.name())
                for option in self.options()
            ] or [0]
        )

        for option in self.options():
            resolved_value = str(self.option(option.name()).get())
            if len(resolved_value) > value_limit:
                resolved_value = resolved_value[:value_limit - 3] + "..."

            print(
                f"        {option.name().ljust(option_len + 2, ' ')} : {resolved_value}")

        print(f"    Inputs :")

        inputs_len = max(
            [
                len(input_.name())
                for input_ in self.inputs()
            ] or [0]
        )

        for input_ in self.inputs():
            resolved_value = str(self.input(input_.name()).get())
            if len(resolved_value) > value_limit:
                resolved_value = resolved_value[:value_limit - 3] + "..."

            print(
                f"        {input_.name().ljust(inputs_len + 2, ' ')} : {resolved_value}")

    # ----------------------------------------------------------------------------------
    def describe_outputs(self):

        print(f"    Outputs :")
        value_limit = 200

        output_len = max(
            [
                len(output.name())
                for output in self.outputs()
            ] or [0]
        )

        for output in self.outputs():
            resolved_value = str(self.output(output.name()).get())
            if len(resolved_value) > value_limit:
                resolved_value = resolved_value[:value_limit - 3] + "..."

            print(
                f"        {output.name().ljust(output_len + 2, ' ')} : {resolved_value}")

    # ----------------------------------------------------------------------------------
    def serialise(self) -> dict:
        """
        This will serialise down the complete state of the component into a dictionary
        format that is json serialisable
        """
        option_data = dict()
        input_data = dict()

        for option in self.options():
            serialised_data = option.serialise()
            option_data[serialised_data["name"]] = serialised_data["value"]

        for input_ in self.inputs():
            serialised_data = input_.serialise()
            input_data[serialised_data["name"]] = serialised_data["value"]

        return dict(
            component_type=self.identifier,
            inputs=input_data,
            options=option_data,
            label=self.label(),
            uuid=self.uuid(),
            enabled=self.is_enabled(),
            children=[
                child.serialise()
                for child in self.children
            ],
        )

    # ----------------------------------------------------------------------------------
    def save_settings(self, filepath):
        """
        This will store this components serialised data to a json file

        Args:
            filepath: Absolute filepath to write to
        """
        data = self.serialise()

        with open(filepath, "w") as f:
            json.dump(
                data,
                f,
                indent=4,
                sort_keys=True,
            )

    # ----------------------------------------------------------------------------------
    def load_settings(self, filepath):
        """
        This will load a json file of settings and attempt to set its own
        inputs and options based on that data

        Args:
            filepath: Aboslute filepath to the settings file to load
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        for name, value in data.get("inputs", {}).items():
            input_ = self.input(name)
            if input_:
                input_.set(value)

        for name, value in data.get("options", {}).items():
            option = self.option(name)
            if option:
                option.set(value)

        self.changed.emit()

    # ----------------------------------------------------------------------------------
    def import_subtree(self, filepath: str) -> None:
        """
        Load a serialised subtree from a JSON file and add the contents
        as children of this component. UUIDs are regenerated to avoid
        collisions; labels are preserved.

        Convenience wrapper for ``self.stack.import_subtree_under(
        self, filepath)``.

        :param filepath: Absolute path to a JSON file produced by
            ``save_settings()`` or ``Stack.save()``.
        """
        self.stack.import_subtree_under(parent=self, filepath=filepath)

    # ----------------------------------------------------------------------------------
    def duplicate(self, input_overrides=None, option_overrides=None, include_children=True):
        """
        Create a duplicate of this component in the stack.

        By default the entire subtree is duplicated — this component and all
        its descendants — and parented as a sibling of the original. Pass
        ``include_children=False`` to copy only this component without its
        children.

        ``input_overrides`` and ``option_overrides`` apply only to the
        top-level duplicate; descendants keep their original values.
        """
        # -- Instance the new component
        new_component = self.stack.add_component(
            component_type=self.identifier,
            label=self.label(),
            suppress_events=True,
        )

        # -- Copy all the data
        new_component.copy(self)

        # -- Apply any overrides (top-level only)
        for name, value in (input_overrides or dict()).items():
            new_component.input(name).set(value)
        for name, value in (option_overrides or dict()).items():
            new_component.option(name).set(value)

        # -- Set the parenting of the component (sibling of the original)
        new_component.set_parent(
            parent=self.parent,
        )

        # -- Recursively duplicate children under the new component. Snapshot
        # -- self.children first because child.duplicate() temporarily inserts
        # -- the new child into its source parent (self) before we reparent
        # -- it under new_component below.
        if include_children:
            for child in list(self.children):
                child_duplicate = child.duplicate(include_children=True)
                child_duplicate.set_parent(parent=new_component)

        # -- Trigger its events
        new_component.on_enter_stack()

        self.stack.component_added.emit(new_component)

        return new_component

    # ----------------------------------------------------------------------------------
    def copy(self, other_component):
        """
        This method will copy all the settings from the given component to this
        component.

        Args:
            other_component: Stack Component to copy settings from

        Returns:

        """
        for input_ in self.inputs():
            input_to_copy = other_component.input(input_.name())

            if input_to_copy:
                self.input(input_.name()).set(
                    copy.deepcopy(input_to_copy.get(resolved=False)),
                )

        for option in self.options():
            option_to_copy = other_component.option(option.name())

            if option_to_copy:
                self.option(option.name()).set(
                    copy.deepcopy(option_to_copy.get(resolved=False)),
                )

        self.set_label(other_component.label())
        self.set_enabled(other_component.is_enabled())

    # ----------------------------------------------------------------------------------
    def documentation(self):
        if not self.__doc__:
            return ""

        lines = []

        for line in self.__doc__.split("\n"):
            line = line.strip()

            if not line:
                line = "\n"

            lines.append(line)

        return " ".join(lines)