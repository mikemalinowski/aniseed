"""
Provides visibility components. "Utility : Show/Hide" sets the visibility
of the given nodes or of their shapes, "Utility : Drive Shape Visibility"
adds an attribute which drives the visibility of the shapes of the given
transforms, and "Utility : Type Driven Show/Hide" shows or hides every node
of the given types found under a set of search roots, using drawStyle for
joints.
"""
import os
import mref
import logging
import aniseed

log = logging.getLogger(__name__)


class VisibilityComponent(aniseed.RigComponent):
    """
    Shows or hides the given nodes, or only their shapes.
    """

    identifier = "Utility : Show/Hide"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes To Set Visibility input and the Visibility and Shapes
        Only options.
        """
        super().__init__(*args, **kwargs)

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
        """
        Returns an object list widget for the Nodes To Set Visibility input.
        """
        if requirement_name == "Nodes To Set Visibility":
            return aniseed.widgets.ObjectList()

    def run(self):
        """
        Sets the visibility of each given node, or of its shapes when Shapes
        Only is on.
        """

        for node_name in self.input("Nodes To Set Visibility").get() or list():
            node = mref.get(node_name)

            nodes_to_affect = [node]
            if self.option("Shapes Only").get():
                nodes_to_affect = node.shapes()

            for node_to_affect in nodes_to_affect:
                node_to_affect.attr("visibility").set(
                    self.option("Visibility").get(),
                )


class DriveShapeVisibility(aniseed.RigComponent):
    """
    Adds a visibility attribute to the attribute host which drives the
    visibility of the shapes of every given transform. Any existing input
    to those shape visibilities is replaced.
    """

    identifier = "Utility : Drive Shape Visibility"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the Attribute Host and Transforms inputs and the Attribute
        Name and Default Value options.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Attribute Host",
            description="The node the visibility attribute is added to",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="Transforms",
            description="The transforms (or addresses) whose shapes the attribute shows and hides",
            value=[],
            validate=True,
            group="Required Nodes",
        )

        self.declare_option(
            name="Attribute Name",
            description="The name of the visibility attribute added to the attribute host",
            value="shape_visibility",
            group="Behaviour",
        )

        self.declare_option(
            name="Default Value",
            description="Whether the shapes are shown by default",
            value=False,
            group="Behaviour",
        )

    def input_widget(self, requirement_name):
        """
        Returns an object list for the Transforms input and an object
        selector for the Attribute Host.
        """
        if requirement_name == "Transforms":
            return aniseed.widgets.ObjectList()

        if requirement_name == "Attribute Host":
            return aniseed.widgets.ObjectSelector(component=self)

    def run(self):
        """
        Adds the attribute (shown in the channel box, not keyable) and
        connects it to the visibility of every shape of each transform.
        """
        host = mref.get(self.input("Attribute Host").get())
        attribute = host.add_attribute(
            self.option("Attribute Name").get(),
            value=self.option("Default Value").get(),
            attribute_type="bool",
            keyable=False,
        )
        attribute.set(channelBox=True)

        for transform in self.input("Transforms").get() or list():
            transform = self._resolve(transform)

            if not transform or not mref.objExists(transform):
                log.warning(f"{self.label()} : {transform!r} does not exist, so its shapes are not driven")
                continue

            for shape in mref.get(transform).shapes():
                attribute.connect(shape.attr("visibility"), force=True)

        return True

    def _resolve(self, value):
        """
        Returns the value of the attribute the given value addresses, or the
        value itself if it is not an address.
        """
        attribute = self.rig.resolve_attribute(value) if value else None
        return attribute.get() if attribute else value


class ObjectTypeVisibility(aniseed.RigComponent):
    """
    Shows or hides every node of the given types found under the given
    search roots. Joints are hidden via their draw style rather than
    their visibility.
    """

    identifier = "Utility : Type Driven Show/Hide"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes To Search Under input and the Node Types to Hide,
        Visible and Shape Only options.
        """
        super().__init__(*args, **kwargs)

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

        # -- Note that this is "Shape Only" whereas the Show/Hide component
        # -- uses "Shapes Only". Both are kept as they are stored in rigs.
        self.declare_option(
            name="Shape Only",
            value=False,
            group="Behaviour",
        )

    def input_widget(self, requirement_name):
        """
        Returns an object list widget for the Nodes To Search Under input.
        """
        if requirement_name == "Nodes To Search Under":
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name):
        """
        Returns a text list widget for the Node Types to Hide option.
        """
        if option_name == "Node Types to Hide":
            return aniseed.widgets.TextList()

    def run(self):
        """
        Gathers every node of the given types beneath the search roots and
        shows or hides them. Joints are toggled via drawStyle (0 or 2), all
        other nodes via visibility. Note the known issue with Shape Only, which
        for non joints gathers same-type descendants rather than shapes.
        """

        nodes_to_affect = list()

        shapes_only = self.option("Shape Only").get()

        for search_root in self.input("Nodes To Search Under").get() or list():
            for node_type in self.option("Node Types to Hide").get() or list():
                for child in mref.get(search_root).children(recursive=True, node_type=node_type):

                    # -- Known issue (kept for parity): for non joints
                    # -- "Shape Only" gathers descendants of the same type,
                    # -- rather than the child's shapes.
                    if shapes_only and node_type != "joint":
                        nodes_to_affect.extend(
                            child.children(recursive=True, node_type=node_type),
                        )

                    else:
                        nodes_to_affect.append(child)

        visible = self.option("Visible").get()

        for node_to_affect in nodes_to_affect:
            if node_to_affect.node_type() == "joint":
                node_to_affect.attr("drawStyle").set(
                    0 if visible else 2,  # -- 2 : Dont Draw anything
                )

            else:
                node_to_affect.attr("visibility").set(visible)
