import os
import qute
import functools
import shapeshift

import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class StoreControlShapes(aniseed.RigComponent):

    identifier = "Utility : Store Control Shapes"
    icon = os.path.join(os.path.dirname(__file__), "store_shapes.png")

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(StoreControlShapes, self).__init__(*args, **kwargs)

        self.declare_option(
            name="Store Data",
            value=True,
        )

        self.declare_option(
            name="Shape Data",
            value=list(),
        )

        self.declare_option(
            name="_Clear Shapes",
            value=None,
        )

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name):
        if option_name == "Shape Data":
            return self.IGNORE_OPTION_FOR_UI

        if option_name == "_Clear Shapes":
            return aniseed.widgets.everywhere.ButtonWidget(
                button_name="Clear Shape Data",
                func=functools.partial(
                    self._clear_shapes,
                    self,
                ),
            )

    # ----------------------------------------------------------------------------------
    def run(self) -> bool:

        if not self.option("Store Data").get():
            return True

        nodes = mc.controller(
            allControllers=True,
            query=True,
        )

        shape_data = list()

        for node in nodes:

            # -- Ensure we're only looking at controls which are part
            # -- of our rig
            if not self.rig.label in mc.ls(node, long=True)[0]:
                continue

            shape_nodes = mc.listRelatives(node, type="nurbsCurve")

            if not shape_nodes:
                continue

            shape_data.append(shapeshift.read(node))

        self.option("Shape Data").set(
            shape_data,
        )

        return True

    # ----------------------------------------------------------------------------------
    @staticmethod
    def _clear_shapes(component):

        confirmation = qute.utilities.request.confirmation(
            title="Clear Shapes",
            label="Are you sure you want to clear the shape data?",
            parent=None,
        )

        if not confirmation:
            return

        component.option("Shape Data").set(
            list(),
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class ApplyControlShapes(aniseed.RigComponent):

    identifier = "Utility : Apply Control Shapes"
    icon = os.path.join(os.path.dirname(__file__), "apply_shapes.png")

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(ApplyControlShapes, self).__init__(*args, **kwargs)

        self.declare_option(
            name="Apply Data",
            value=True,
        )

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name):
        if option_name == "Shape Data":
            return self.IGNORE_OPTION_FOR_UI

        return None

    # ----------------------------------------------------------------------------------
    def run(self) -> bool:

        if not self.option("Apply Data").get():
            return True

        stored_shape_data = list()

        # -- Find the store component so we can extract the data
        for component in self.rig.components():
            if isinstance(component, StoreControlShapes):
                stored_shape_data: list = component.option("Shape Data").get()

        if not stored_shape_data:
            return True

        for shape_data in stored_shape_data:

            node = shape_data["node"]

            if not mc.objExists(node):
                continue

            connection_data = list()
            for shape in mc.listRelatives(node, shapes=True) or list():
                connection_data = mc.listConnections(
                    shape,
                    source=True,
                    plugs=True,
                    connections=True,
                ) or list()

                break

            shapeshift.apply(node, shape_data)

        return True