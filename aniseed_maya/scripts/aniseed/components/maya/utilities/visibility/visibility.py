import os
import aniseed
import maya.cmds as mc


class VisibilityComponent(aniseed.RigComponent):

    identifier = "Utility : Show/Hide"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(VisibilityComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes To Set Visibility",
            validate=True,
            group="Required Nodes",
        )

        self.declare_option(
            name="Visibility",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Shapes Only",
            value=False,
            group="Behaviour",
        )

    def input_widget(self, requirement_name):
        if requirement_name == "Nodes To Set Visibility":
            return aniseed.widgets.ObjectList()

    def run(self):

        for node in self.input("Nodes To Set Visibility").get() or list():

            nodes_to_affect = []

            if self.option("Shapes Only").get():
                nodes_to_affect = mc.listRelatives(node, shapes=True) or list()

            else:
                nodes_to_affect.append(node)

            for node_to_affect in nodes_to_affect:
                mc.setAttr(
                    f"{node_to_affect}.visibility",
                    self.option("Visibility").get(),
                )


class ObjectTypeVisibility(aniseed.RigComponent):

    identifier = "Utility : Type Driven Show/Hide"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(ObjectTypeVisibility, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes To Search Under",
            validate=True,
            value=[],
            group="Required Nodes",
        )

        self.declare_option(
            name="Node Types to Hide",
            value=[],
            group="Behaviour",
        )

        self.declare_option(
            name="Visible",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Shape Only",
            value=False,
            group="Behaviour",
        )

    def input_widget(self, requirement_name):
        if requirement_name == "Nodes To Search Under":
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name):
        if option_name == "Node Types to Hide":
            return aniseed.widgets.TextList()

    def run(self):

        nodes_to_affect = list()

        shapes_only = self.option("Shape Only").get()

        for search_root in self.input("Nodes To Search Under").get() or list():
            for node_type in self.option("Node Types to Hide").get() or list():
                for child in mc.listRelatives(search_root, ad=True, type=node_type) or list():

                    if shapes_only:
                        if node_type == "joint":
                            nodes_to_affect.append(child)

                        else:
                            nodes_to_affect.extend(
                                mc.listRelatives(
                                    child,
                                    ad=True,
                                    type=node_type,
                                ) or list()
                            )

                    else:
                        nodes_to_affect.append(child)


        for node_to_affect in nodes_to_affect:
            if mc.nodeType(node_to_affect) == "joint":
                mc.setAttr(
                    f"{node_to_affect}.drawStyle",
                    0 if self.option("Visible").get() else 2, # -- Dont Draw anything
                )

            else:
                mc.setAttr(
                    f"{node_to_affect}.visibility",
                    self.option("Visible").get(),
                )
