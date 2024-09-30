import os

import aniseed_everywhere as ani
from crosswalk import app


# --------------------------------------------------------------------------------------
class AddSubStructureComponent(ani.RigComponent):

    identifier = "Utility : Add Sub Structure"
    icon = os.path.join(
        os.path.dirname(__file__),
        "add_sub_structure.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(AddSubStructureComponent, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Parent",
            description="Typically the root of the rig",
            validate=True,
            group="Control Rig",
        )

        self.declare_option(
            name="Sub Nodes",
            value=[],
            group="Behaviour",
        )

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name):
        if option_name == "Sub Nodes":
            return ani.widgets.TextList()

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name):
        if requirement_name == "Parent":
            return ani.widgets.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self):

        parent = self.requirement("Parent").get()

        existing_nodes = app.objects.get_children(parent)

        for sub_node in self.option("Sub Nodes").get():

            resolved_name = self.config.generate_name(
                classification=self.config.organisational,
                description=sub_node,
                location=self.config.middle,
                unique=False,
            )

            if resolved_name in existing_nodes:
                continue

            node = app.objects.create(
                name=resolved_name,
                parent=parent,
            )

        return True


# --------------------------------------------------------------------------------------
class DeleteChildren(ani.RigComponent):

    identifier = "Utility : Delete Children"
    icon = os.path.join(
        os.path.dirname(__file__),
        "delete_children.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(DeleteChildren, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Node",
            value=""
        )

        self.declare_option(
            name="Include Self",
            value=False,
        )

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name):
        if requirement_name == "Node":
            return ani.widgets.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self) -> bool:

        node = self.requirement("Node").get()

        if not app.objects.exists(node):
            return True

        for child in app.objects.get_children(node):
            if app.objects.exists(child):
                app.objects.delete(child)

        if self.option("Include Self").get():
            app.objects.delete(node)

        return True
