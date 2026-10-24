"""
Provides the "Dev Example : Options And Inputs" component, which sets one
attribute to one value on a list of nodes.

What this example teaches:
    * Declaring inputs and options in __init__
    * The difference between an input and an option
    * Reading their values with .get()
    * Using description, group and pre_expose to shape the ui
    * Choosing a widget for an input with input_widget

Read next: ex03_validation.py
"""
import logging

# -- maya.cmds is used to set the attribute values
from maya import cmds

import aniseed

log = logging.getLogger(__name__)


class OptionsAndInputs(aniseed.RigComponent):
    """
    Sets the given attribute to the given value on every node in Nodes.
    """

    identifier = "Dev Example : Options And Inputs"

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes input and the Attribute Name and Value options.
        """
        # -- Always call the base class first. It creates the lists that
        # -- declare_input, declare_option and declare_output add to, along
        # -- with the label and the stack, so nothing can be declared before it.
        super().__init__(*args, **kwargs)

        # -- Key idea: an INPUT is something from the scene that this component
        # -- works on, such as a node name. An input can be wired to the output
        # -- of another component (see ex09_simple_control.py), in which case its
        # -- value is only known once the build is running.
        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes to set the attribute on",
            # -- Inputs and options with the same group are shown together
            # -- under that heading in the app
            group="Scene",
        )

        # -- An OPTION is a setting which changes how the component behaves.
        # -- The type of the default value decides which widget the app shows
        # -- (str -> line edit, float -> spin box, bool -> check box) unless
        # -- option_widget returns a widget of our own (see ex05_colour_nodes_cmds.py).
        self.declare_option(
            name="Attribute Name",
            value="displayLocalAxis",
            description="The name of the attribute to set, such as visibility",
            group="Behaviour",
            # -- pre_expose shows this option in the dialog the app shows when
            # -- the component is first added, so the user can set it up front
            pre_expose=True,
        )

        self.declare_option(
            name="Value",
            value=1.0,
            description="The value to set the attribute to",
            group="Behaviour",
            pre_expose=True,
        )

    def input_widget(self, requirement_name):
        """
        Returns an object list for the Nodes input, which has buttons to fill
        it from the Maya selection.
        """
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()

        # -- Returning None means the app chooses a widget from the value type
        return None

    def run(self):
        """
        Sets the attribute on every node.
        """
        # -- .get() returns the current value. If the input is wired to
        # -- another component's output, .get() follows the wire and returns
        # -- that output's value instead.
        nodes = self.input("Nodes").get()

        # -- A wired input may hold a single node name rather than a list,
        # -- such as when it is wired to an output holding one control
        if isinstance(nodes, str):
            nodes = [nodes]

        attribute_name = self.option("Attribute Name").get()
        value = self.option("Value").get()

        for node in nodes:
            cmds.setAttr(f"{node}.{attribute_name}", value)

        log.info(f"{self.label()} set {attribute_name} to {value} on {len(nodes)} node(s)")
