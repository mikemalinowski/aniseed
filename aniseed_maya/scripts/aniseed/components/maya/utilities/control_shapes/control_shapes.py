import os
import aniseed
import qtility
import functools
import traceback
import aniseed_toolkit

import maya.cmds as mc


# noinspection PyUnresolvedReferences
class StoreControlShapes(aniseed.RigComponent):

    identifier = "Utility : Store Control Shapes"
    icon = os.path.join(os.path.dirname(__file__), "store_shapes.png")

    def __init__(self, *args, **kwargs):
        super(StoreControlShapes, self).__init__(*args, **kwargs)

        self.declare_option(
            name="Store Data",
            value=True,
        )

        self.declare_option(
            name="Shape Data",
            value=list(),
            hidden=True,
        )

        self.declare_option(
            name="Transient Shape Data",
            value=list(),
            hidden=True,
        )
        self.declare_option(
            name="_Clear Shapes",
            value=None,
        )

    def option_widget(self, option_name):
        if option_name == "_Clear Shapes":
            return aniseed.widgets.ButtonWidget(
                button_name="Clear Shape Data",
                func=functools.partial(
                    self._clear_shapes,
                    self,
                ),
            )

    def run(self) -> bool:

        if not self.option("Store Data").get():
            return True

        nodes = mc.controller(
            allControllers=True,
            query=True,
        )

        shape_data = list()
        read = list()

        for node in nodes:

            # -- Ensure we're only looking at controls which are part
            # -- of our rig
            if not self.rig.label in mc.ls(node, long=True)[0]:
                continue

            shape_nodes = mc.listRelatives(node, type="nurbsCurve")

            if not shape_nodes:
                continue

            shape_data.append(
                aniseed_toolkit.run(
                    "Read Shape From Node",
                    node,
                ),
            )
            read.append(node)

        for existing_data in self.option("Shape Data").get() or list():
            if existing_data["node"] not in read:
                shape_data.append(existing_data)

        self.option("Transient Shape Data").set(
            shape_data,
        )

        return True

    def on_build_finished(self, successful: bool) -> None:

        if successful:
            self.option("Shape Data").set(
                self.option("Transient Shape Data").get(),
            )
            self.option("Transient Shape Data").set(list())

    @staticmethod
    def _clear_shapes(component):

        confirmation = qtility.request.confirmation(
            title="Clear Shapes",
            message="Are you sure you want to clear the shape data?",
            parent=None,
        )

        if not confirmation:
            return

        component.option("Shape Data").set(
            list(),
        )


# noinspection PyUnresolvedReferences
class ApplyControlShapes(aniseed.RigComponent):

    identifier = "Utility : Apply Control Shapes"
    icon = os.path.join(os.path.dirname(__file__), "apply_shapes.png")

    def __init__(self, *args, **kwargs):
        super(ApplyControlShapes, self).__init__(*args, **kwargs)

        self.declare_option(
            name="Apply Data",
            value=True,
        )

    def run(self) -> bool:

        if not self.option("Apply Data").get():
            return True

        stored_shape_data = list()

        # -- Find the store component so we can extract the data
        for component in self.rig.components():
            if isinstance(component, StoreControlShapes):
                option_name = "Shape Data"
                if component.option("Transient Shape Data").get():
                    option_name = "Transient Shape Data"
                stored_shape_data: list = component.option(option_name).get()

        if not stored_shape_data:
            return True

        for shape_data in stored_shape_data:

            node = shape_data["node"]

            if not mc.objExists(node):
                continue

            connection_pairs = []
            for shape in mc.listRelatives(node, shapes=True) or list():
                connection_data = mc.listConnections(
                    shape,
                    source=True,
                    plugs=True,
                    connections=True,
                ) or list()

                for idx in range(int(len(connection_data) * 0.5)):
                    stage = idx * 2
                    destination_attribute = connection_data[stage].split(".")[-1]
                    driving_attribute = connection_data[stage+1]

                    connection_pairs.append([driving_attribute, destination_attribute])

            aniseed_toolkit.run(
                "Apply Shape",
                node=node,
                data=shape_data,
            )

            for connection_pair in connection_pairs:
                for shape in mc.listRelatives(node, shapes=True) or list():
                    driving_attribute = connection_pair[0]
                    destination_attribute = f"{shape}.{connection_pair[1]}"

                    try:
                        mc.connectAttr(driving_attribute, destination_attribute)
                    except:
                        traceback.print_exc()
                        pass


        return True
