"""
Provides the control colouring components. "Utility : Color Controls"
recolours every curve control in the scene based on the location token in
its name, falling back to the middle colour. "Utility : Color Specific
Controls" applies a single colour to a given list of nodes, and a deprecated
wrapper keeps the misspelled "Utility : Color Specifc Controls" identifier
loading for older rigs.
"""
import os
import aniseed
import aniseed_toolkit


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
        """
        Declares a colour option for each of the left, middle and right
        locations (tracked in _colour_options) and a Nodes To Skip option.
        """
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
                group="Colors",
            )

        self.declare_option(
            name="Nodes To Skip",
            value=[],
            description="List of objects to skip when applying colours",
            group="Object Filtering"
        )

    def option_widget(self, option_name):
        """
        Returns a colour picker for each colour option and an object list
        for Nodes To Skip.
        """
        if option_name in self._colour_options:
            return aniseed.widgets.ColorPicker(
                default_colour=self.option(option_name).get(),
            )

        if option_name == "Nodes To Skip":
            return aniseed.widgets.ObjectList()
        return None

    def run(self) -> bool:
        """
        Applies the colour matching each curve control's location token,
        falling back to the middle colour, and skipping any control listed
        in Nodes To Skip.
        """
        colours_by_location = {
            self.config.left:   self.option("Left Color").get(),
            self.config.middle: self.option("Middle Color").get(),
            self.config.right:  self.option("Right Color").get(),
        }
        fallback = colours_by_location[self.config.middle]
        controls_to_skip = self.option("Nodes To Skip").get()

        for node in aniseed_toolkit.control_queries.curve_controls():
            if node in controls_to_skip:
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
        """
        Declares the Nodes input and the Color option.
        """
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
        """
        Returns an object list for every input (only Nodes is declared).
        """
        return aniseed.widgets.ObjectList()

    def option_widget(self, option_name):
        """
        Returns a colour picker for the Color option.
        """
        if option_name == "Color":
            return aniseed.widgets.ColorPicker(
                default_colour=self.option("Color").get(),
            )

        return None

    def run(self) -> bool:
        """
        Applies the Color option to every node in Nodes which has curve
        shapes. Nodes without curve shapes are silently skipped.
        """
        nodes = self.input("Nodes").get()
        colour = self.option("Color").get()

        for node in nodes:
            if aniseed_toolkit.control_queries.has_curve_shapes(node):
                aniseed_toolkit.shapes.apply_color(node, *colour)

        return True


# noinspection PyUnresolvedReferences
class ColorSpecificControlsDeprecatedSpellingErrorWrapper(ColorSpecificControls):
    """
    Deprecated : Kept so rigs saved with the misspelled identifier still
    load. Use Color Specific Controls instead.
    """

    identifier = "Utility : Color Specifc Controls"
    deprecated = True
