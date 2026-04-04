import mref
import aniseed
from maya import cmds


class SetDrivenKey(aniseed.RigComponent):

    identifier = "Utility : Set Driven Key"

    def __init__(self, *args, **kwargs):
        super(SetDrivenKey, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Source Node",
            value="",
        )

        self.declare_input(
            name="Source Attribute",
            value="",
        )

        self.declare_input(
            name="Destination Node",
            value="",
        )

        self.declare_input(
            name="Destination Attribute",
            value="",
        )

        self.declare_option(
            name="Force",
            value=True,
        )

        self.declare_option(
            name="Curve Data",
            value={'name': 'UNITLESS', 'animCurveType': 7, 'isWeighted': False, 'preInfinity': 0, 'postInfinity': 0, 'keys': [{'time': 0.0, 'value': 0.0, 'inTangentType': 'linear', 'outTangentType': 'linear', 'inTangentX': 1.0, 'inTangentY': 0.0, 'outTangentX': 0.7071067811865475, 'outTangentY': 0.7071067811865475, 'lockTangents': True, 'inWeight': 1.0, 'outWeight': 1.0, 'weightLock': False, 'weightedTangents': False}, {'time': 1.0, 'value': 1.0, 'inTangentType': 'linear', 'outTangentType': 'linear', 'inTangentX': 0.7071067811865475, 'inTangentY': 0.7071067811865475, 'outTangentX': 1.0, 'outTangentY': 0.0, 'lockTangents': True, 'inWeight': 1.0, 'outWeight': 1.0, 'weightLock': False, 'weightedTangents': False}]},
            hidden=True,
        )

        self.declare_option(
            name="Curve Path",
            value="",
            hidden=True
        )
        self.declare_option(
            name="Store Curve Data",
            value="",
        )

    def input_widget(self, requirement_name):
        """
        This allows us to provide dedicate widgets for specific inputs
        """
        if requirement_name in ["Source Node", "Destination Node"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str) -> "PySide6.QWidget":
        if option_name == "Store Curve Data":
            return aniseed.widgets.ButtonWidget(
                button_name="Store Set Driven Key Data",
                func=self.user_func_store_curve,
            )

    def run(self):

        source_node = mref.get(self.input("Source Node").get())
        source_attribute_name = self.input("Source Attribute").get()
        destination_node = mref.get(self.input("Destination Node").get())
        destination_attribute_name = self.input("Destination Attribute").get()

        source_attribute = source_node.attr(source_attribute_name)
        destination_attribute = destination_node.attr(destination_attribute_name)

        # -- Hook up the curve node
        curve_node = mref.create("animCurveUU")
        source_attribute.connect(curve_node.attr("input"))
        curve_node.attr("output").connect(destination_attribute)

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
