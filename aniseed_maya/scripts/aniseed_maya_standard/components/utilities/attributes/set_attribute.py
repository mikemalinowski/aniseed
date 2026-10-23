"""
Provides the "Utility : Set Attribute (Multi)" component, which sets the
same attribute to the same value on a list of nodes. The value is given as a
string and coerced into each attribute's python type, with booleans resolved
from common truthy/falsy strings. An Ignore Errors option controls whether
unresolvable nodes are skipped or raise.
"""
import logging
import mref
import aniseed

log = logging.getLogger(__name__)


_TRUTHY_STRINGS = frozenset({"true", "1", "yes", "on"})
_FALSY_STRINGS = frozenset({"", "false", "0", "no", "off"})


def _coerce(raw_value: str, python_type: type):
    """
    Converts the given string value to the given python type. Booleans are
    resolved from common truthy/falsy strings rather than python's bool(),
    which would treat any non-empty string as True.
    """
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
        """
        Declares the Nodes, Attribute and Value inputs, along with an Ignore
        Errors option for nodes which cannot be resolved.
        """
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
            description="If true, nodes that do not exist are skipped with a warning rather than failing the build.",
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object list widget for the Nodes input. Other inputs use
        the default widget.
        """
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()

    def run(self):
        """
        Sets the named attribute on every node to the coerced Value. Nodes
        which cannot be resolved are reported and either skipped or raise,
        depending on Ignore Errors. Attributes with no python type are
        skipped. A missing attribute still fails regardless of Ignore Errors
        (a known issue noted in the code).
        """
        attribute_name = self.input("Attribute").get()
        raw_value = self.input("Value").get()

        for node_name in self.input("Nodes").get():

            # -- A missing node is returned by mref.get as a plain string,
            # -- which has no attr method. Known issue (kept for parity): a
            # -- missing attribute gives None here rather than raising, so
            # -- it fails on python_type below regardless of Ignore Errors.
            try:
                attribute = mref.get(node_name).attr(attribute_name)

            except AttributeError:
                if not self.option("Ignore Errors").get():
                    raise Exception(f"Could not set attribute on {node_name}")
                log.warning(f"Could not set attribute on {node_name}, skipping")
                continue

            python_type = attribute.python_type()

            if python_type is None:
                continue

            attribute.set(_coerce(raw_value, python_type))
