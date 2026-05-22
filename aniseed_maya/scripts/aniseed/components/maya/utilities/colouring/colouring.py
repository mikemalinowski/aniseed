import os
import aniseed
import aniseed_toolkit

import maya.cmds as mc


# noinspection PyUnresolvedReferences
class ColorControls(aniseed.RigComponent):

    identifier = "Utility : Color Controls"
    icon = os.path.join(os.path.dirname(__file__), "colouring.png")

    def __init__(self, *args, **kwargs):
        super(ColorControls, self).__init__(*args, **kwargs)

        self._colour_options = {
            "Left Color": [235, 107, 73],
            "Middle Color": [242, 222, 111],
            "Right Color": [111, 157, 242],
        }

        for color_label, default_color in self._colour_options.items():
            self.declare_option(
                name=color_label,
                value=default_color,
            )

    def option_widget(self, option_name):
        if option_name in self._colour_options:
            return aniseed.widgets.ColorPicker(
                default_colour=self.option(option_name).get(),
            )

        return None

    def run(self) -> bool:

        nodes = mc.controller(
            allControllers=True,
            query=True,
        )

        for node in nodes:

            shapes = mc.listRelatives(node, type="nurbsCurve")

            if not shapes:
                continue

            color = None
            location = self.config.extract_location(node)

            # -- Get the colour
            if location == self.config.left:
                color = self.option("Left Color").get()

            if location == self.config.middle:
                color = self.option("Middle Color").get()

            if location == self.config.right:
                color = self.option("Right Color").get()

            if not color:
                color = self.option("Middle Color").get()

            aniseed_toolkit.shapes.apply_color(
                node,
                *color
            )

        return True


# noinspection PyUnresolvedReferences
class ColorSpecificControls(aniseed.RigComponent):

    identifier = "Utility : Color Specifc Controls"
    icon = os.path.join(os.path.dirname(__file__), "colouring.png")

    def __init__(self, *args, **kwargs):
        super(ColorSpecificControls, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
        )

        self.declare_option(
            name="Color",
            value=[242, 222, 111],
        )

    def input_widget(self, requirement_name: str) -> "PySide6.QWidget":
        return aniseed.widgets.ObjectList()

    def option_widget(self, option_name):
        if option_name == "Color":
            return aniseed.widgets.ColorPicker(
                default_colour=self.option("Color").get(),
            )

        return None

    def run(self) -> bool:

        nodes = self.input("Nodes").get()
        color = self.option("Color").get()

        for node in nodes:

            shapes = mc.listRelatives(node, type="nurbsCurve")

            if not shapes:
                continue

            aniseed_toolkit.shapes.apply_color(
                node,
                *color
            )

        return True
