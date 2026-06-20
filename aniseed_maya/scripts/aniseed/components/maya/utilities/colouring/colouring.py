import os
import aniseed
import aniseed_toolkit

from maya import cmds


# noinspection PyUnresolvedReferences
class ColorControls(aniseed.RigComponent):
    """
    Walks every controller in the scene and recolours its NURBS curve
    shapes based on the location token in each control's name. Controls
    on the left/middle/right pick up their corresponding option colour;
    controls without a recognised location fall back to the middle colour.
    """

    identifier = "Utility : Color Controls"
    icon = os.path.join(os.path.dirname(__file__), "colouring.png")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._colour_options = {
            "Left Color": {
                "default": [235, 107, 73],
                "description": "RGB colour applied to controls whose name resolves to the 'left' location token.",
            },
            "Middle Color": {
                "default": [242, 222, 111],
                "description": "RGB colour applied to controls whose name resolves to the 'middle' location, and used as the fallback for controls with no recognised location.",
            },
            "Right Color": {
                "default": [111, 157, 242],
                "description": "RGB colour applied to controls whose name resolves to the 'right' location token.",
            },
        }

        for color_label, spec in self._colour_options.items():
            self.declare_option(
                name=color_label,
                value=spec["default"],
                description=spec["description"],
            )

    def option_widget(self, option_name):
        if option_name in self._colour_options:
            return aniseed.widgets.ColorPicker(
                default_colour=self.option(option_name).get(),
            )

        return None

    def run(self) -> bool:
        colours_by_location = {
            self.config.left:   self.option("Left Color").get(),
            self.config.middle: self.option("Middle Color").get(),
            self.config.right:  self.option("Right Color").get(),
        }
        fallback = colours_by_location[self.config.middle]

        nodes = cmds.controller(allControllers=True, query=True)

        for node in nodes:
            if not cmds.listRelatives(node, type="nurbsCurve"):
                continue

            location = self.config.extract_location(node)
            colour = colours_by_location.get(location, fallback)
            aniseed_toolkit.shapes.apply_color(node, *colour)

        return True


# noinspection PyUnresolvedReferences
class ColorSpecificControls(aniseed.RigComponent):
    """
    Recolours the NURBS curve shapes of a specific list of nodes to a
    single user-chosen colour, ignoring any location tokens in their
    names.
    """

    identifier = "Utility : Color Specific Controls"
    icon = os.path.join(os.path.dirname(__file__), "colouring.png")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes whose curve shapes will be recoloured.",
        )

        self.declare_option(
            name="Color",
            value=[242, 222, 111],
            description="The RGB colour applied to every node in Nodes.",
        )

    def input_widget(self, requirement_name: str):
        return aniseed.widgets.ObjectList()

    def option_widget(self, option_name):
        if option_name == "Color":
            return aniseed.widgets.ColorPicker(
                default_colour=self.option("Color").get(),
            )

        return None

    def run(self) -> bool:
        nodes = self.input("Nodes").get()
        colour = self.option("Color").get()

        for node in nodes:
            if not cmds.listRelatives(node, type="nurbsCurve"):
                continue

            aniseed_toolkit.shapes.apply_color(node, *colour)

        return True

# noinspection PyUnresolvedReferences
class ColorSpecificControlsDeprecatedSpellingErrorWrapper(ColorSpecificControls):
    """
    Recolours the NURBS curve shapes of a specific list of nodes to a
    single user-chosen colour, ignoring any location tokens in their
    names.
    """

    identifier = "Utility : Color Specifc Controls"
    deprecated = True
