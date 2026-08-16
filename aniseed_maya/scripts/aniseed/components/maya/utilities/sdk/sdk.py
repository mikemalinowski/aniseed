import typing

import mref
import aniseed
from maya import cmds


class SetDrivenKey(aniseed.RigComponent):
    """
    Drives one attribute from another via an animCurveUU node, with the
    curve shape stored on the component so the same SDK rebuilds
    identically across rig rebuilds. The 'Store Set Driven Key Data'
    button captures the current curve back into the component.
    """

    identifier = "Utility : Set Driven Key"

    _DEFAULT_CURVE_DATA = {
        'name': 'UNITLESS',
        'animCurveType': 7,
        'isWeighted': False,
        'preInfinity': 0,
        'postInfinity': 0,
        'keys': [
            {
                'time': 0.0,
                'value': 0.0,
                'inTangentType': 'linear',
                'outTangentType': 'linear',
                'inTangentX': 1.0,
                'inTangentY': 0.0,
                'outTangentX': 0.7071067811865475,
                'outTangentY': 0.7071067811865475,
                'lockTangents': True,
                'inWeight': 1.0,
                'outWeight': 1.0,
                'weightLock': False,
                'weightedTangents': False,
            },
            {
                'time': 1.0,
                'value': 1.0,
                'inTangentType': 'linear',
                'outTangentType': 'linear',
                'inTangentX': 0.7071067811865475,
                'inTangentY': 0.7071067811865475,
                'outTangentX': 1.0,
                'outTangentY': 0.0,
                'lockTangents': True,
                'inWeight': 1.0,
                'outWeight': 1.0,
                'weightLock': False,
                'weightedTangents': False,
            },
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Source Node",
            value="",
            description="The node that owns the attribute driving the relationship.",
        )

        self.declare_input(
            name="Source Attribute",
            value="",
            description="The name of the attribute on the Source Node whose value drives the curve.",
        )

        self.declare_input(
            name="Destination Node",
            value="",
            description="The node that owns the attribute being driven.",
        )

        self.declare_input(
            name="Destination Attribute",
            value="",
            description="The name of the attribute on the Destination Node that the curve writes into.",
        )

        self.declare_option(
            name="Force",
            value=True,
            description="If true, the source-to-curve and curve-to-destination connections are made with force=True so they replace any existing incoming connection on those attributes.",
        )

        self.declare_option(
            name="Curve Data",
            value=self._DEFAULT_CURVE_DATA,
            hidden=True,
            description="Internal storage for the captured animCurveUU shape (keys, tangents, infinity modes). Updated by the 'Store Set Driven Key Data' button.",
        )

        self.declare_option(
            name="Curve Path",
            value="",
            hidden=True,
            description="Internal storage for the name of the curve node created during the last build, used to look the node up when capturing curve data.",
        )
        self.declare_option(
            name="Store Curve Data",
            value=None,
            description="Press 'Store Set Driven Key Data' to capture the current shape of the live curve back into Curve Data, so it rebuilds identically next time.",
        )

    def input_widget(self, requirement_name):
        if requirement_name in ["Source Node", "Destination Node"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        if option_name == "Store Curve Data":
            return aniseed.widgets.ButtonWidget(
                button_name="Store Set Driven Key Data",
                func=self.user_func_store_curve,
            )

    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Select Curve": self.user_func_select_curve,
        }

    def is_valid(self) -> bool:
        for input_name in (
            "Source Node",
            "Source Attribute",
            "Destination Node",
            "Destination Attribute",
        ):
            if not self.input(input_name).get():
                print(f"{input_name} is required")
                return False

        return True

    def run(self):

        source_node = mref.get(self.input("Source Node").get())
        source_attribute_name = self.input("Source Attribute").get()
        destination_node = mref.get(self.input("Destination Node").get())
        destination_attribute_name = self.input("Destination Attribute").get()
        force = self.option("Force").get()

        source_attribute = source_node.attr(source_attribute_name)
        destination_attribute = destination_node.attr(destination_attribute_name)

        # -- Hook up the curve node
        curve_node = mref.create(
            "animCurveUU",
            name=self.config.generate_name(
                classification="mech",
                description=f"SDK_{destination_attribute_name}",
            ),
        )
        source_attribute.connect(curve_node.attr("input"), force=force)
        curve_node.attr("output").connect(destination_attribute, force=force)

        # -- Set the curve data
        curve_node.construct_from_dictionary(
            self.option("Curve Data").get() or dict(),
        )

        self.option("Curve Path").set(curve_node.name())

        return True

    def user_func_store_curve(self):
        curve_name = self.option("Curve Path").get()

        if curve_name and cmds.objExists(curve_name):
            curve = mref.get(curve_name)
            self.option("Curve Data").set(curve.to_dictionary())

    def user_func_select_curve(self):
        curve_name = self.option("Curve Path").get()

        if curve_name and cmds.objExists(curve_name):
            cmds.select(curve_name)
