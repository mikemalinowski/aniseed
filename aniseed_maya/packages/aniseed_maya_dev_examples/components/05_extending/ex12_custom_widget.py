"""
Provides the "Dev Example : Custom Widget" component, which sets the radius of
joints, using a slider widget written for this package.

What this example teaches:
    * Using your own widget for an option
    * Where to put widget code: the package's widgets folder
    * Using a hidden option to configure a widget

The widget itself is in aniseed_maya_dev_examples/widgets/slider_spin_box.py.

Read next: ex13_using_a_mixin.py
"""
import logging

# -- maya.cmds is used to set the joint radius
from maya import cmds

import aniseed

# -- Key idea: component files are loaded by their file path, not imported as
# -- modules, so one component file cannot import from another. Code shared
# -- between components (such as widgets) goes in the package's widgets (or
# -- mixins) folder, which is importable by the package's name.
from aniseed_maya_dev_examples.widgets import SliderSpinBox

log = logging.getLogger(__name__)


class CustomWidgetExample(aniseed.RigComponent):
    """
    Sets the display radius of the given joints. Drag the slider, or type an
    exact value.
    """

    identifier = "Dev Example : Custom Widget"

    def __init__(self, *args, **kwargs):
        """
        Declares the Joints input, the Joint Radius option and the hidden
        Slider Range option.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Joints",
            value=[],
            description="The joints to set the radius of",
            group="Scene",
        )

        self.declare_option(
            name="Joint Radius",
            value=1.0,
            description="The radius to give each joint",
            group="Visuals",
            pre_expose=True,
        )

        # -- A hidden option is stored in the recipe but never shown. Here it
        # -- holds the slider's range, so a technical director can change it in
        # -- the recipe (or from code) without the user seeing it in the app.
        self.declare_option(
            name="_Slider Range",
            value=[0.1, 10.0],
            hidden=True,
            description="The minimum and maximum values of the Joint Radius slider",
        )

    def option_widget(self, option_name):
        """
        Returns a SliderSpinBox for the Joint Radius option.
        """
        if option_name == "Joint Radius":
            minimum, maximum = self.option("_Slider Range").get()

            # -- The app takes it from here: it calls set_value with the stored
            # -- value, connects to the widget's changed signal, and calls
            # -- get_value to store the new value whenever it fires
            return SliderSpinBox(minimum=minimum, maximum=maximum)

        return None

    def input_widget(self, requirement_name):
        """
        Returns an object list for the Joints input.
        """
        if requirement_name == "Joints":
            return aniseed.widgets.ObjectList()
        return None

    def run(self):
        """
        Sets the radius of every joint.
        """
        # -- run only ever reads the option's value. Widgets only exist while
        # -- the app is showing this component, and not at all when a rig is
        # -- built without the app (such as in mayapy), so run must never
        # -- depend on one.
        radius = self.option("Joint Radius").get()

        joints = self.input("Joints").get()

        # -- A wired input may hold a single node name rather than a list
        if isinstance(joints, str):
            joints = [joints]

        for joint in joints:
            cmds.setAttr(f"{joint}.radius", radius)

        return True
