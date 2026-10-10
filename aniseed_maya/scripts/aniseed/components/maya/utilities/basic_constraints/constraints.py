import mref
import aniseed
import aniseed_toolkit
from maya import cmds


class ParentConstraint(aniseed.RigComponent):
    """
    Creates a control that blends the rotation of a joint between two
    target nodes. A "Blend" attribute on the control (0.0 to 1.0) drives
    a pair of parent constraints between Target A and Target B, while the
    control itself drives the joint's transform.
    """

    identifier = "Utility : Parent Constraint"

    def __init__(self, *args, **kwargs):
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
        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:

        maintain_offset = self.option("Maintain Offset").get()
        include_scale = self.option("Include Scale").get()

        mref.parentConstraint(
            self.input("Constrain To").get(),
            self.input("Node To Constrain").get(),
            maintainOffset=maintain_offset,
        )

        if include_scale:
            mref.scaleConstraint(
                self.input("Constrain To").get(),
                self.input("Node To Constrain").get(),
                maintainOffset=maintain_offset,
            )