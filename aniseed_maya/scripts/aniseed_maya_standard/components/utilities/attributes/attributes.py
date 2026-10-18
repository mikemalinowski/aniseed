"""
Provides the "Utility : Add Attribute" component, which adds a single
attribute to a host node using a configurable name, type and initial value.
The created attribute's full node.attr name is exposed as an output for
downstream components. The value is coerced by evaluating "<type>(<value>)",
so only types which are also python builtins (such as float or int) work.
"""
import mref
import aniseed


# noinspection PyUnresolvedReferences
class AddAttributeComponent(aniseed.RigComponent):
    """
    Adds a single attribute to a host node, with a configurable name, type
    and initial value. The new attribute is exposed as an output so that
    downstream components can bind to it.
    """

    identifier = "Utility : Add Attribute"

    def __init__(self, *args, **kwargs):
        """
        Declares the Host input, options for the attribute's name, type,
        initial value, keyable and channel box state, and the Attribute output.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Host",
            value="",
            description="The node that the new attribute will be added to.",
        )

        self.declare_option(
            name="Attribute Name",
            value="Attribute",
            description="The long name to give the new attribute.",
        )

        self.declare_option(
            name="Attribute Type",
            value="float",
            description="The Maya attribute type (e.g. float, bool, enum, message).",
        )

        self.declare_option(
            name="Attribute Value",
            value="",
            description="The initial value to set on the new attribute. Leave empty to use the type's default.",
        )

        self.declare_option(
            name="Channel Box",
            value=True,
            description="The initial value to set on the new attribute. Leave empty to use the type's default.",
        )
        self.declare_option(
            name="Keyable",
            value=True,
            description="The initial value to set on the new attribute. Leave empty to use the type's default.",
        )

        self.declare_output(
            name="Attribute",
            description="The fully-qualified name (node.attr) of the attribute that was created.",
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for every input (only Host is declared).
        """
        return aniseed.widgets.ObjectSelector()

    def run(self):
        """
        Adds the attribute to the host node and writes its full node.attr
        name to the Attribute output. The value is built by evaluating
        "<type>(<value>)", so only types which are also python builtins (such
        as float or int) work - see the known issue noted in the code. The
        Channel Box option is only applied when the attribute is not keyable.
        """
        attribute_type = self.option("Attribute Type").get()
        keyable = self.option("Keyable").get()

        # -- The value is coerced by evaluating "<attribute type>(<value>)".
        # -- Known issue (kept for parity): this only works where the maya
        # -- attribute type is also a python builtin (e.g. float, int), an
        # -- empty value gives the builtin's default (e.g. float() -> 0.0),
        # -- and types such as long, double, enum or string raise a NameError.
        value = eval(f"{attribute_type}({self.option('Attribute Value').get()})")

        attribute = mref.get(self.input("Host").get()).add_attribute(
            self.option("Attribute Name").get(),
            value=value,
            attribute_type=attribute_type,
            keyable=keyable,
        )

        if not keyable:
            attribute.set(channelBox=self.option("Channel Box").get())

        self.output("Attribute").set(attribute.name(include_node=True))
