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
    return python_type(raw_value)


class SetAttributeMany(aniseed.RigComponent):
    """
    Sets the same attribute to the same value on a list of nodes. The value
    is coerced from a string into the attribute's underlying Python type
    before being applied.
    """

    identifier = "Utility : Set Attribute (Multi)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes that the attribute will be set on. Each node must already have the named attribute.",
        )

        self.declare_input(
            name="Attribute",
            value="",
            description="The name of the attribute to set on every node in Nodes.",
        )

        self.declare_input(
            name="Value",
            value="",
            validate=False,
            description="The value to apply, given as a string. It is coerced into the attribute's Python type before being set.",
        )

        self.declare_option(
            name="Ignore Errors",
            value=False,
            description="",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()

    def run(self):
        node_names = self.input("Nodes").get()
        attribute_name = self.input("Attribute").get()
        raw_value = self.input("Value").get()

        for node_name in node_names:
            node = mref.get(node_name)

            try:
                attribute = node.attr(attribute_name)

            except AttributeError:
                print(f"Could not set attribute on {node_name}")
                if not self.option("Ignore Errors").get():
                   raise Exception(f"Could not set attribute on {node_name}")
                else:
                    continue
                    
            python_type = attribute.python_type()

            if python_type is None:
                continue

            attribute.set(_coerce(raw_value, python_type))
