"""
Provides the "Dev Example : Utility Network" component, which builds a small
network of utility nodes that measures the distance between two nodes and
drives an attribute with how far that distance has stretched.

What this example teaches:
    * Creating DG (non DAG) nodes and connecting their attributes
    * Outputting an attribute, rather than a node
    * Reporting a clear error rather than letting Maya raise a vague one

Read next: ../04_data/ex11_stored_values.py
"""
import logging

# -- maya.cmds is the only Maya API this example uses
from maya import cmds

import aniseed

log = logging.getLogger(__name__)


class UtilityNetwork(aniseed.RigComponent):
    """
    Measures the distance from Start to End, divides it by the distance when
    the rig was built, and connects the result into the Driven Attribute of
    the Driven Node. The result is 1.0 at rest, 2.0 when the distance doubles,
    and so on.
    """

    identifier = "Dev Example : Utility Network"

    def __init__(self, *args, **kwargs):
        """
        Declares the Start, End and Driven Node inputs, the naming and Driven
        Attribute options, and the Distance Node, Ratio Node and Ratio
        Attribute outputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Start",
            value="",
            description="The node to measure from",
            group="Scene",
        )

        self.declare_input(
            name="End",
            value="",
            description="The node to measure to",
            group="Scene",
        )

        self.declare_input(
            name="Driven Node",
            value="",
            description="The node whose attribute is driven by the stretch ratio",
            group="Scene",
        )

        self.declare_option(
            name="Driven Attribute",
            value="scaleX",
            description="The attribute on the Driven Node to connect the stretch ratio into",
            group="Behaviour",
            pre_expose=True,
        )

        self.declare_option(
            name="Description",
            value="stretch",
            description="Used when naming the utility nodes",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value=self.config.middle,
            description="The location (side) token used when naming",
            group="Naming",
        )

        self.declare_output(
            name="Distance Node",
            description="The distanceBetween node measuring Start to End",
        )
        self.declare_output(
            name="Ratio Node",
            description="The multiplyDivide node dividing the distance by the rest distance",
        )

        # -- Key idea: an output can hold any plain value, not just a node.
        # -- This one holds "node.attribute", so another component can connect
        # -- the ratio into something else.
        self.declare_output(
            name="Ratio Attribute",
            description="The attribute holding the stretch ratio, such as md_mch_stretchRatio_01.outputX",
            is_default=True,
        )

    def option_widget(self, option_name):
        """
        Returns a location selector for the Location option.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(
                self.config,
                value=self.option("Location").get(),
            )
        return None

    def input_widget(self, requirement_name):
        """
        Returns an object selector for each node input.
        """
        if requirement_name in ("Start", "End", "Driven Node"):
            return aniseed.widgets.ObjectSelector(component=self)
        return None

    def is_valid(self) -> bool:
        """
        Checks the nodes exist and that the Driven Node has the Driven
        Attribute, for every input which is not wired to another component.
        """
        for input_name in ("Start", "End", "Driven Node"):
            node_input = self.input(input_name)

            if node_input.is_address() or not node_input.get():
                continue

            if not cmds.objExists(node_input.get()):
                log.warning(f"{self.label()} : {input_name} {node_input.get()!r} does not exist")
                return False

        driven_input = self.input("Driven Node")
        attribute_name = self.option("Driven Attribute").get()

        if not driven_input.is_address() and driven_input.get():
            if not cmds.attributeQuery(attribute_name, node=driven_input.get(), exists=True):
                log.warning(f"{self.label()} : {driven_input.get()} has no {attribute_name} attribute")
                return False

        return True

    def run(self):
        """
        Creates and connects the distanceBetween and multiplyDivide nodes.
        """
        start = self.input("Start").get()
        end = self.input("End").get()
        driven_plug = f"{self.input('Driven Node').get()}.{self.option('Driven Attribute').get()}"

        description = self.option("Description").get()
        location = self.option("Location").get()

        # -- Check this before creating anything, so a failure leaves nothing
        # -- half built. Maya's own error ("already has an incoming
        # -- connection") would not say which component caused it.
        existing = cmds.listConnections(driven_plug, source=True, destination=False, plugs=True)
        if existing:
            raise RuntimeError(
                f"{self.label()} : {driven_plug} is already driven by {existing[0]}. "
                f"Disconnect it, or choose another attribute."
            )

        # -- Utility nodes are DG nodes: they have no transform and do not
        # -- appear in the outliner's hierarchy, so they need no parent. The
        # -- configuration's "mechanical" classification marks them as nodes
        # -- the animator should never touch.
        distance_node = cmds.createNode(
            "distanceBetween",
            name=self.config.generate_name(self.config.mechanical, f"{description}_distance", location),
        )

        # -- worldMatrix[0] is the node's world space matrix, so the distance
        # -- is measured in world space whatever the nodes are parented under
        cmds.connectAttr(f"{start}.worldMatrix[0]", f"{distance_node}.inMatrix1")
        cmds.connectAttr(f"{end}.worldMatrix[0]", f"{distance_node}.inMatrix2")

        # -- Read the distance now, while the rig is in its rest pose
        rest_distance = cmds.getAttr(f"{distance_node}.distance")
        if rest_distance < 1e-6:
            raise RuntimeError(f"{self.label()} : {start} and {end} are in the same place")

        ratio_node = cmds.createNode(
            "multiplyDivide",
            name=self.config.generate_name(self.config.mechanical, f"{description}_ratio", location),
        )

        # -- operation 2 is divide: outputX = input1X / input2X
        cmds.setAttr(f"{ratio_node}.operation", 2)
        cmds.connectAttr(f"{distance_node}.distance", f"{ratio_node}.input1X")
        cmds.setAttr(f"{ratio_node}.input2X", rest_distance)

        ratio_attribute = f"{ratio_node}.outputX"
        cmds.connectAttr(ratio_attribute, driven_plug)

        self.output("Distance Node").set(distance_node)
        self.output("Ratio Node").set(ratio_node)
        self.output("Ratio Attribute").set(ratio_attribute)

        return True
