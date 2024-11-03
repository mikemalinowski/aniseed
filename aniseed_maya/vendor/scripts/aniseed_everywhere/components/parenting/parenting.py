import aniseed_everywhere as ani

from crosswalk import app


# --------------------------------------------------------------------------------------
class ReParentComponent(ani.RigComponent):

    identifier = "Utility : Reparent"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(ReParentComponent, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Node To Re-Parent",
            validate=True,
            group="Required Nodes",
        )

        self.declare_requirement(
            name="New Parent",
            validate=False,
            group="Required Nodes",
        )

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name):

        if requirement_name == "Node To Re-Parent":
            return ani.widgets.ObjectSelector(component=self)

        if requirement_name == "New Parent":
            return ani.widgets.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self):

        node_to_reparent = self.requirement("Node To Re-Parent").get()
        new_parent = self.requirement("New Parent").get()

        try:
            app.objects.set_parent(
                node_to_reparent,
                new_parent
            )

        except:
            pass
