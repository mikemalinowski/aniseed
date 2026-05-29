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

        if requirement_name in ("Node To Re-Parent", "New Parent"):
            return aniseed.widgets.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self):

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
