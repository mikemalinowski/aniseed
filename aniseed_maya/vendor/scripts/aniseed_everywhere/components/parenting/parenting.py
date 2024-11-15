import crosswalk
import aniseed_everywhere


# --------------------------------------------------------------------------------------
class ReParentComponent(aniseed_everywhere.RigComponent):

    identifier = "Utility : Reparent"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(ReParentComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Node To Re-Parent",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="New Parent",
            validate=False,
            group="Required Nodes",
        )

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name):

        if requirement_name == "Node To Re-Parent":
            return aniseed_everywhere.widgets.ObjectSelector(component=self)

        if requirement_name == "New Parent":
            return aniseed_everywhere.widgets.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self):

        node_to_reparent = self.input("Node To Re-Parent").get()
        new_parent = self.input("New Parent").get()

        try:
            crosswalk.app.objects.set_parent(
                node_to_reparent,
                new_parent
            )

        except:
            pass
