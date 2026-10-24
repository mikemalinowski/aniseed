"""
Provides the "Dev Example : Colour Nodes (cmds)" component, which sets the
draw override colour of existing nodes, using only maya.cmds.

What this example teaches:
    * A "modifier": a component which changes nodes that already exist
      and creates nothing
    * Choosing a widget for an option with option_widget
    * Working with the values a widget stores (here, 0-255 colours)

Compare with: ex06_lock_and_hide_openmaya.py, a modifier written with OpenMaya.

Read next: ex06_lock_and_hide_openmaya.py
"""
import logging

# -- maya.cmds is the only Maya API this example uses
from maya import cmds

import aniseed

log = logging.getLogger(__name__)


class ColourNodesCmds(aniseed.RigComponent):
    """
    Sets the draw override colour of the given nodes. Turn on Apply To
    Shapes to colour their shapes instead, which is usually what you want for
    controls with several shapes.
    """

    identifier = "Dev Example : Colour Nodes (cmds)"

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes input and the Colour and Apply To Shapes options.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes to colour",
            group="Scene",
        )

        # -- The ColorPicker widget stores colours as [red, green, blue] in
        # -- the 0-255 range, so the default uses the same form
        self.declare_option(
            name="Colour",
            value=[255, 170, 0],
            description="The colour to apply",
            group="Behaviour",
            pre_expose=True,
        )

        self.declare_option(
            name="Apply To Shapes",
            value=True,
            description="If on, the shapes of each node are coloured rather than the node itself",
            group="Behaviour",
        )

    def option_widget(self, option_name):
        """
        Returns a colour picker for the Colour option.
        """
        # -- Key idea: without this, the app would show the colour as a plain
        # -- list of numbers. The widget is given the current value so it can
        # -- show it straight away.
        if option_name == "Colour":
            return aniseed.widgets.ColorPicker(
                default_colour=self.option("Colour").get(),
            )

        # -- Returning None means the app chooses a widget from the value type
        return None

    def input_widget(self, requirement_name):
        """
        Returns an object list for the Nodes input.
        """
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()
        return None

    def run(self):
        """
        Turns on the RGB draw override of every target and sets its colour.
        """
        nodes = self.input("Nodes").get()

        # -- A wired input may hold a single node name rather than a list
        if isinstance(nodes, str):
            nodes = [nodes]

        # -- Maya's override colour is 0-1, but the widget stores 0-255
        red, green, blue = [channel / 255.0 for channel in self.option("Colour").get()]

        for node in nodes:
            for target in self._targets(node):
                cmds.setAttr(f"{target}.overrideEnabled", True)
                cmds.setAttr(f"{target}.overrideRGBColors", True)
                cmds.setAttr(f"{target}.overrideColorRGB", red, green, blue)

        return True

    def _targets(self, node):
        """
        Returns the nodes to colour for the given node: its shapes when
        Apply To Shapes is on and it has any, otherwise the node itself.
        """
        if self.option("Apply To Shapes").get():
            # -- fullPath avoids errors when two shapes share a short name.
            # -- listRelatives returns None, not an empty list, when nothing
            # -- is found, hence the "or []".
            shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
            if shapes:
                return shapes

        return [node]
