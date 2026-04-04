import mref
import aniseed
from maya import cmds


class ConstrainBetween(aniseed.RigComponent):

    identifier = "Utility : Constrain Between"

    def __init__(self, *args, **kwargs):
        super(ConstrainBetween, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Node To Constraint",
            value="",
        )

        self.declare_input(
            name="First Constraint Target",
            value="",
        )

        self.declare_input(
            name="Second Constraint Target",
            value="",
        )

        self.declare_option(
            name="Maintain Offset",
            value=False,
        )

        self.declare_option(
            name="Constraint Type",
            value="parentConstraint",
        )

        self.declare_option(
            name="Default Blend",
            value=0.5,
        )

        self.declare_input(
            name="Attribute Host",
            value="",
        )

        self.declare_option(
            name="Attribute Label",
            value="",
        )

    def input_widget(self, requirement_name):
        """
        This allows us to provide dedicate widgets for specific inputs
        """

        object_list = [
            "Node To Constraint",
            "First Constraint Target",
            "Second Constraint Target",
            "Attribute Host",
        ]

        if requirement_name in object_list:
            return aniseed.widgets.ObjectSelector(component=self)

    def run(self):

        node_to_cosntrain = mref.get(self.input("Node To Constraint").get())
        target_a = mref.get(self.input("First Constraint Target").get())
        target_b = mref.get(self.input("Second Constraint Target").get())

        constraint_type = self.option("Constraint Type").get()

        constraint_func = getattr(cmds, constraint_type)

        constraint_func(
            target_a.full_name(),
            node_to_cosntrain.full_name(),
            maintainOffset=self.option("Maintain Offset").get(),
        )

        constraint = mref.get(
            constraint_func(
                target_b.full_name(),
                node_to_cosntrain.full_name(),
                maintainOffset=self.option("Maintain Offset").get(),
            )[0],
        )

        attribute_host = self.input("Attribute Host").get()

        if not attribute_host:
            return

        cmds.refresh()
        weight_attributes = constraint.weight_attributes()

        attribute = mref.get(attribute_host).add_attribute(
            self.option("Attribute Label").get(),
            value=self.option("Default Blend").get(),
            attribute_type="float",
        )
        reverse_node = mref.create("reverse")

        attribute.connect(reverse_node.attr("inputX"))
        reverse_node.attr("outputX").connect(
            constraint.attr(weight_attributes[0])
        )
        attribute.connect(constraint.attr(weight_attributes[1]))