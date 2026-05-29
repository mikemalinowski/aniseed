import os
import crosswalk
import aniseed


# --------------------------------------------------------------------------------------
class AddSubStructureComponent(aniseed.RigComponent):
    """
    Adds a set of organisational child nodes under a given parent.

    The names of the children are drawn from the "Sub Nodes" option;
    each one is resolved through the rig's naming convention as an
    organisational node at the middle location. Existing children with
    matching names are reused rather than recreated.

    Outputs for each sub-node are declared dynamically inside ``run()``
    based on the current "Sub Nodes" list, so other components can
    reference them by sub-node name after the build has been run.
    """

    identifier = "Utility : Add Sub Structure"
    icon = os.path.join(
        os.path.dirname(__file__),
        "add_sub_structure.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="Typically the root of the rig",
            validate=True,
            group="Control Rig",
        )

        self.declare_option(
            name="Sub Nodes",
            description=(
                "List of sub-node names to create beneath the parent. "
                "Each entry produces an organisational node and an "
                "output of the same name."
            ),
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

        for output in self.outputs():
            self.remove_output(output.name())

        parent = self.input("Parent").get()

        existing_nodes = crosswalk.items.get_children(parent)

        for sub_node in self.option("Sub Nodes").get():

            resolved_name = self.config.generate_name(
                classification=self.config.organisational,
                description=sub_node,
                location=self.config.middle,
                unique=False,
            )
            self.declare_output(name=sub_node)
            self.output(sub_node).set(resolved_name)

            if resolved_name in existing_nodes:
                continue

            crosswalk.items.create(
                name=resolved_name,
                parent=parent,
            )

        return True


# --------------------------------------------------------------------------------------
class DeleteChildren(aniseed.RigComponent):
    """
    Deletes the immediate children of a given node, and optionally the
    node itself. No-op if the node does not exist.
    """

    identifier = "Utility : Delete Children"
    icon = os.path.join(
        os.path.dirname(__file__),
        "delete_children.png",
    )

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Node",
            description="The node whose children should be deleted.",
            group="Required Nodes",
        )

        self.declare_option(
            name="Include Self",
            description=(
                "If enabled, the node itself is also deleted after its "
                "children have been removed."
            ),
            value=False,
            group="Behaviour",
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
            # -- Deleting one child can cascade-delete its siblings
            # -- (instances, constrained nodes, etc.), so the explicit
            # -- existence check here is intentional — by the time we
            # -- reach later iterations the name may already be gone.
            if crosswalk.items.exists(child):
                crosswalk.items.delete(child)

        if self.option("Include Self").get():
            crosswalk.items.delete(node)
        return True
