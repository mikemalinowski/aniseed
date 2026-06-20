import mref
import aniseed
from maya import cmds


class ConstrainBetween(aniseed.RigComponent):
    """
    Constrains a node between two targets using a pair of constraints of
    the chosen type (parent/point/orient/scale). Optionally exposes a
    blend attribute on a host node that drives the weighting between the
    two targets via a reverse node.
    """

    identifier = "Utility : Constrain Between"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Node To Constrain",
            value="",
            description="The node that will be constrained between the two targets.",
        )

        self.declare_input(
            name="First Constraint Target",
            value="",
            description="The first target. When the blend attribute is 0.0, the constrained node follows this target.",
        )

        self.declare_input(
            name="Second Constraint Target",
            value="",
            description="The second target. When the blend attribute is 1.0, the constrained node follows this target.",
        )

        self.declare_option(
            name="Maintain Offset",
            value=False,
            description="If true, the current offset between the node and each target is preserved at the moment the constraint is created.",
        )

        self.declare_option(
            name="Constraint Type",
            value="parentConstraint",
            description="The Maya cmds constraint function to use (e.g. parentConstraint, pointConstraint, orientConstraint, scaleConstraint).",
        )

        self.declare_option(
            name="Default Blend",
            value=0.5,
            description="The initial value of the blend attribute (0.0 = first target, 1.0 = second target). Only used when Attribute Host is set.",
        )

        self.declare_input(
            name="Attribute Host",
            value="",
            description="Optional. The node on which the blend attribute will be created. Leave empty to skip creating the blend attribute and keep both constraints at their default weights.",
        )

        self.declare_option(
            name="Attribute Label",
            value="",
            description="The name of the blend attribute created on the Attribute Host.",
        )

    def input_widget(self, requirement_name):
        """
        This allows us to provide dedicate widgets for specific inputs
        """

        object_list = [
            "Node To Constrain",
            "First Constraint Target",
            "Second Constraint Target",
            "Attribute Host",
        ]

        if requirement_name in object_list:
            return aniseed.widgets.ObjectSelector(component=self)

    def run(self):
        node_to_constrain = mref.get(self.input("Node To Constrain").get())
        target_a = mref.get(self.input("First Constraint Target").get())
        target_b = mref.get(self.input("Second Constraint Target").get())
        attribute_host = self.input("Attribute Host").get()

        constraint_type = self.option("Constraint Type").get()
        maintain_offset = self.option("Maintain Offset").get()
        default_blend = self.option("Default Blend").get()
        attribute_label = self.option("Attribute Label").get()

        constraint_func = getattr(cmds, constraint_type)

        constraint_func(
            target_a.full_name(),
            node_to_constrain.full_name(),
            maintainOffset=maintain_offset,
        )

        constraint = mref.get(
            constraint_func(
                target_b.full_name(),
                node_to_constrain.full_name(),
                maintainOffset=maintain_offset,
            )[0],
        )

        if not attribute_host:
            return

        weight_attributes = constraint.weight_attributes()

        attribute = mref.get(attribute_host).add_attribute(
            attribute_label,
            value=default_blend,
            attribute_type="float",
        )
        reverse_node = mref.create("reverse")

        attribute.connect(reverse_node.attr("inputX"))
        reverse_node.attr("outputX").connect(weight_attributes[0])
        attribute.connect(weight_attributes[1])