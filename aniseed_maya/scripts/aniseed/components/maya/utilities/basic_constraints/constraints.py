"""
Provides the "Utility : Parent Constraint" component, which parent
constrains one node to another. Options control whether the offset is
maintained and whether a scale constraint is added alongside the parent
constraint.
"""
import mref
import aniseed
import aniseed_toolkit


class ParentConstraint(aniseed.RigComponent):
    """
    Parent constrains a node to another node, optionally also adding a
    scale constraint between them.
    """

    identifier = "Utility : Parent Constraint"

    def __init__(self, *args, **kwargs):
        """
        Declares the Node To Constrain and Constrain To inputs, plus the
        Maintain Offset and Include Scale options.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Node To Constrain",
            value="",
            validate=True,
        )

        self.declare_input(
            name="Constrain To",
            value="",
            validate=True,
        )

        self.declare_option(
            name="Maintain Offset",
            value=True,
        )
        self.declare_option(
            name="Include Scale",
            value=True,
        )

    def input_widget(self, requirement_name):
        """
        Returns an object selector for both inputs.
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        """
        Constrains the node to the driver. When Include Scale is enabled a
        parent and scale constraint pair is created, otherwise just a parent
        constraint. Returns None despite the bool annotation.
        """
        driver = self.input("Constrain To").get()
        driven = self.input("Node To Constrain").get()
        maintain_offset = self.option("Maintain Offset").get()

        if self.option("Include Scale").get():
            aniseed_toolkit.constraints.parent_and_scale(
                driver,
                driven,
                maintain_offset=maintain_offset,
            )

        else:
            mref.parentConstraint(
                driver,
                driven,
                maintainOffset=maintain_offset,
            )
