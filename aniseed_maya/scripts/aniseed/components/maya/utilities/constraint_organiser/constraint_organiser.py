import aniseed
import mref
from maya import cmds


class ConstraintOrganiser(aniseed.RigComponent):
    """
    Walks a hierarchy from a root node, collects every constraint on
    every descendant, and reparents all of those constraints under a
    single chosen node. Useful for keeping the outliner tidy by herding
    constraints out of the deformation hierarchy and into a dedicated
    holding group.
    """

    identifier = "Utility : Constraint Organiser"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Hierarchy Root",
            value="",
            description="The root of the hierarchy to scan. Every descendant is inspected for constraints.",
        )

        self.declare_input(
            name="Constraint Parent",
            value="",
            description="The node under which every constraint found in the hierarchy will be reparented.",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Constraint Parent", "Hierarchy Root"]:
            return aniseed.widgets.ObjectSelector()

    def run(self):

        node = mref.get(self.input("Hierarchy Root").get())
        constraint_parent = self.input("Constraint Parent").get()
        constraints = []

        for child in node.children(recursive=True, include_shapes=False):
            constraints.extend(child.constraints())

        for constraint in constraints:
            cmds.parent(
                constraint.full_name(),
                constraint_parent,
            )
