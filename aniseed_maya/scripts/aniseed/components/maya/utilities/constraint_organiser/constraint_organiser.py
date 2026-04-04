import aniseed
import mref
from maya import cmds


class ConstraintOrganiser(aniseed.RigComponent):

    identifier = "Utility : Constraint Organiser"

    def __init__(self, *args, **kwargs):
        super(ConstraintOrganiser, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Hierarchy Root",
            value="",
        )

        self.declare_input(
            name="Constraint Parent",
            value="",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Constraint Parent", "Hierarchy Root"]:
            return aniseed.widgets.ObjectSelector()

    def run(self):

        node = mref.get(self.input("Hierarchy Root").get())
        constraint_parent = self.input("Constraint Parent").get()
        constraints = []

        for child in node.children(recursive=True):
            constraints.extend(child.constraints())

        for constraint in constraints:
            cmds.parent(
                constraint.full_name(),
                constraint_parent,
            )
