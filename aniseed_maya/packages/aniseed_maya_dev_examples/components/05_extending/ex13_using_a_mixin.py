"""
Provides the "Dev Example : Using A Mixin" component, which tags nodes with a
string attribute, and uses LoggingMixin to record what it did.

What this example teaches:
    * Adding a mixin to a component, and the order of the base classes
    * Calling mixin helpers from run
    * Menu entries from a mixin (mixin_functions) alongside the component's
      own (user_functions)

The mixin itself is in aniseed_maya_dev_examples/mixins/logging_mixin.py.

Read next: ../06_composite/ex14_add_child_components.py
"""
import typing

# -- maya.cmds is used to add and set the tag attribute
from maya import cmds

import aniseed

# -- Like widgets, mixins live in the package's importable mixins folder
from aniseed_maya_dev_examples.mixins import LoggingMixin


# -- Key idea: RigComponent comes first. Python looks for methods in the
# -- order the base classes are listed, so RigComponent's methods (and our
# -- own) win over the mixin's. The mixin only adds new methods, and its
# -- mixin_functions menu entries.
class UsingAMixin(aniseed.RigComponent, LoggingMixin):
    """
    Adds a string attribute called devExampleTag to each node and sets it to
    the Tag option. Use "Print Build Log" and "Select Touched Nodes" from the
    menu to see what the last build did.
    """

    identifier = "Dev Example : Using A Mixin"

    # -- The name of the attribute this component adds
    TAG_ATTRIBUTE = "devExampleTag"

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes input and the Tag option.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes to tag",
            group="Scene",
        )

        self.declare_option(
            name="Tag",
            value="dev_example",
            description="The value to store in each node's devExampleTag attribute",
            group="Behaviour",
            pre_expose=True,
        )

    def input_widget(self, requirement_name):
        """
        Returns an object list for the Nodes input.
        """
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()
        return None

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Adds this component's own menu entry. The app shows these alongside
        the entries from LoggingMixin.mixin_functions.
        """
        return {
            "Remove Tags": self.remove_tags,
        }

    def run(self):
        """
        Adds (if needed) and sets the tag attribute on every node, logging
        each step through the mixin.
        """
        # -- Clear the mixin's record of the previous build
        self.begin_log()

        nodes = self.input("Nodes").get()

        # -- A wired input may hold a single node name rather than a list
        if isinstance(nodes, str):
            nodes = [nodes]

        tag = self.option("Tag").get()

        for node in nodes:

            if not cmds.attributeQuery(self.TAG_ATTRIBUTE, node=node, exists=True):
                cmds.addAttr(node, longName=self.TAG_ATTRIBUTE, dataType="string")
                self.log_step(f"Added {self.TAG_ATTRIBUTE} to {node}")

            cmds.setAttr(f"{node}.{self.TAG_ATTRIBUTE}", tag, type="string")
            self.log_step(f"Tagged {node} with {tag!r}")

        self.record_touched(nodes)
        return True

    def remove_tags(self):
        """
        Removes the tag attribute from every node the last build touched.
        """
        for node in self.touched_nodes():
            if cmds.objExists(node) and cmds.attributeQuery(self.TAG_ATTRIBUTE, node=node, exists=True):
                cmds.deleteAttr(f"{node}.{self.TAG_ATTRIBUTE}")
