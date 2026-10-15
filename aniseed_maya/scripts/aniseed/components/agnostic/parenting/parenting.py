"""
Provides the "Utility : Reparent" component, which parents a scene node under
another node, or under the world if no new parent is given. A failed reparent
is reported but does not fail the build.
"""
import crosswalk
import aniseed


# --------------------------------------------------------------------------------------
class ReParentComponent(aniseed.RigComponent):
    """
    Re-parents a scene node under another. If "New Parent" is empty,
    the node is moved to the world (i.e. unparented).
    """

    identifier = "Utility : Reparent"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """
        Declares the "Node To Re-Parent" input and the optional "New Parent"
        input (left empty to unparent to the world).
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Node To Re-Parent",
            description="The scene node whose parent will be changed.",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="New Parent",
            description=(
                "The node to make the new parent. Leave empty to "
                "unparent the node to the world."
            ),
            validate=False,
            group="Required Nodes",
        )

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name):
        """
        Returns an object selector for both the "Node To Re-Parent" and
        "New Parent" inputs.

        Args:
            requirement_name: The name of the input to return a widget for.
        """

        if requirement_name in ("Node To Re-Parent", "New Parent"):
            return aniseed.widgets.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self):
        """
        Parents the node under the new parent (or the world if no parent is
        given). Any exception raised by the reparent is caught and printed, so
        a failed reparent does not fail the build.
        """

        node_to_reparent = self.input("Node To Re-Parent").get()
        new_parent = self.input("New Parent").get()

        try:
            crosswalk.items.set_parent(
                node_to_reparent,
                new_parent,
            )

        except Exception:
            print(
                f"[aniseed] Reparent failed: "
                f"{node_to_reparent!r} -> {new_parent!r}"
            )
