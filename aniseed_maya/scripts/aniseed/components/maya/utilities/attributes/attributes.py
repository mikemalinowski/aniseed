import mref
import aniseed

_TRUTHY_STRINGS = frozenset({"true", "1", "yes", "on"})
_FALSY_STRINGS = frozenset({"", "false", "0", "no", "off"})


def _coerce(raw_value: str, python_type: type):
    if python_type is bool:
        normalised = raw_value.strip().lower()
        if normalised in _TRUTHY_STRINGS:
            return True
        if normalised in _FALSY_STRINGS:
            return False
        raise ValueError(
            f"Cannot coerce {raw_value!r} to bool. "
            f"Expected one of: {sorted(_TRUTHY_STRINGS | _FALSY_STRINGS)}."
        )
    return eval(f"{python_type}({raw_value})")


# noinspection PyUnresolvedReferences
class AddAttributeComponent(aniseed.RigComponent):
    """
    Adds a single attribute to a host node, with a configurable name, type
    and initial value. The new attribute is exposed as an output so that
    downstream components can bind to it.
    """

    identifier = "Utility : Add Attribute"

    def __init__(self, *args, **kwargs):
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
        return aniseed.widgets.ObjectSelector()

    def run(self):
        host = self.input("Host").get()
        attribute_name = self.option("Attribute Name").get()
        attribute_type = self.option("Attribute Type").get()
        attribute_value = self.option("Attribute Value").get()
        node = mref.get(host)

        # python_type = attribute.python_type()
        value = _coerce(attribute_value, attribute_type)
        attribute = node.add_attribute(
            attribute_name,
            # value=attribute_value,
            value=value,
            attribute_type=attribute_type,
            keyable=self.option("Keyable").get(),
        )
        # python_type = attribute.python_type()
        # attribute.set(_coerce(attribute_value, python_type))
        if not self.option("Keyable").get():
            attribute.set(channelBox=self.option("Channel Box").get())

        self.output("Attribute").set(attribute.name(include_node=True))