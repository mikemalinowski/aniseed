import mref
import aniseed


# noinspection PyUnresolvedReferences
class AddAttributeComponent(aniseed.RigComponent):

    identifier = "Utility : Add Attribute"

    def __init__(self, *args, **kwargs):
        super(AddAttributeComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Host",
            value="",
        )

        self.declare_option(
            name="Attribute Name",
            value="Attribute",
        )

        self.declare_option(
            name="Attribute Type",
            value="float",
        )

        self.declare_option(
            name="Attribute Value",
            value="",
        )

        self.declare_output(
            name="Attribute",
        )

    def input_widget(self, requirement_name: str):
        return aniseed.widgets.ObjectSelector()

    def run(self):
        node = mref.get(self.input("Host").get())

        attribute = node.add_attribute(
            self.option("Attribute Name").get(),
            value=self.option("Attribute Value").get(),
            atttribute_type=self.option("Attribute Type").get(),
        )

        self.output("Attribute").set(attribute.name(include_node=True))