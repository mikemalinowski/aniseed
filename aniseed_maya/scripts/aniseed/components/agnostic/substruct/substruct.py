import os
import crosswalk
import aniseed


# --------------------------------------------------------------------------------------
class AddSubStructureComponent(aniseed.RigComponent):

    identifier = "Utility : Add Sub Structure"
    icon = os.path.join(
        os.path.dirname(__file__),
        "add_sub_structure.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(AddSubStructureComponent, self).__init__(*args, **kwargs)

        self.declare_input(
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
            return aniseed.widgets.TextList()

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name):
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self):

        parent = self.input("Parent").get()

        existing_nodes = crosswalk.items.get_children(parent)

        for sub_node in self.option("Sub Nodes").get():

            resolved_name = self.config.generate_name(
                classification=self.config.organisational,
                description=sub_node,
                location=self.config.middle,
                unique=False,
            )

            if resolved_name in existing_nodes:
                continue

            node = crosswalk.items.create(
                name=resolved_name,
                parent=parent,
            )

        return True


# --------------------------------------------------------------------------------------
class DeleteChildren(aniseed.RigComponent):

    identifier = "Utility : Delete Children"
    icon = os.path.join(
        os.path.dirname(__file__),
        "delete_children.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(DeleteChildren, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Node",
            value="",
        )

        self.declare_option(
            name="Include Self",
            value=False,
        )

    # ----------------------------------------------------------------------------------
    def input_widget(self, requirement_name):
        if requirement_name == "Node":
            return aniseed.widgets.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self) -> bool:

        node = self.input("Node").get()

        if not crosswalk.items.exists(node):
            return True

        for child in crosswalk.items.get_children(node):
            if crosswalk.items.exists(child):
                crosswalk.items.delete(child)

        if self.option("Include Self").get():
            crosswalk.items.delete(node)

        return True
