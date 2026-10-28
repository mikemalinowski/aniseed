"""
Provides the "Utility : Constraint Organiser" component, which gathers every
constraint found on the descendants of a hierarchy root and reparents them
under a single chosen node. This keeps constraints out of the deformation
hierarchy and tidies the outliner.
"""
import aniseed
import mref


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
        """
        Declares the Hierarchy Root and Constraint Parent inputs.
        """
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
        """
        Returns an object selector for both inputs.
        """
        if requirement_name in ["Constraint Parent", "Hierarchy Root"]:
            return aniseed.widgets.ObjectSelector()

    def run(self):
        """
        Gathers the constraints on every descendant of the hierarchy root
        and reparents them under the constraint parent. Errors if a
        constraint is already parented there.
        """

        node = mref.get(self.input("Hierarchy Root").get())
        constraint_parent = self.input("Constraint Parent").get()

        # -- Gather everything before reparenting, so that moving the
        # -- constraints does not alter the hierarchy being walked
        constraints = []
        for child in node.children(recursive=True, include_shapes=False):
            constraints.extend(child.constraints())

        # -- mref.parent (cmds passthrough) rather than set_parent, as
        # -- set_parent would silently skip, rather than error on, a
        # -- constraint which is already under the constraint parent
        for constraint in constraints:
            mref.parent(constraint, constraint_parent)
