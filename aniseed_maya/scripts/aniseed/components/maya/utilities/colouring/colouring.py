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
            return aniseed.widgets.everywhere.ColorPicker(
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
            location = aniseed_toolkit.run("Get Control", node).location

            # -- Get the colour
            if location.lower() == self.config.left:
                color = self.option("Left Color").get()

            if location.lower() == self.config.middle:
                color = self.option("Middle Color").get()

            if location.lower() == self.config.right:
                color = self.option("Right Color").get()

            if not color:
                color = self.option("Middle Color").get()

            nodes_to_colour = [node]
            nodes_to_colour.extend(shapes)

            for shape in shapes:
                mc.setAttr(f"{shape}.overrideEnabled", True)
                mc.setAttr(f"{shape}.overrideRGBColors", True)
                mc.setAttr(f"{shape}.useOutlinerColor", True)

                for idx, channel in enumerate(["R", "G", "B"]):
                    mc.setAttr(f"{shape}.overrideColor{channel}", color[idx] / 255.0)
                    mc.setAttr(f"{shape}.outlinerColor{channel}", color[idx] / 255.0)

        return True
