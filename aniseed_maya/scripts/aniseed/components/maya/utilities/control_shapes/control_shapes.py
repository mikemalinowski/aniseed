import os
import json
import aniseed
import qtility
import functools
import aniseed_toolkit

import maya.cmds as mc


# noinspection PyUnresolvedReferences
class StoreControlShapes(aniseed.RigComponent):
    """
    Deprecated : Do not continue to use this component. The Apply Shape Data component
    now has functionality to snapshot and hold the shape data it applies.
    """
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

    def run(self) -> bool:
        return True


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

        self.declare_option(
            name="Skip Nodes",
            value=list(),
            hidden=False,
        )

        self.declare_option(
            name="Shape Data",
            value=list(),
            hidden=True,
        )

        self.declare_option(
            name="Snapshot Shape Data",
            value=None,
        )

        self.declare_option(
            name="Clear Shape Data",
            value=None,
        )

        self.declare_option(
            name="Save Shape Data File",
            value=None,
        )

        self.declare_option(
            name="Load Shape Data File",
            value=None,
        )

    def option_widget(self, option_name):
        if option_name == "Skip Nodes":
            return aniseed.widgets.ObjectList()

        if option_name == "Snapshot Shape Data":
            return aniseed.widgets.ButtonWidget(
                button_name="Snapshot Shape Data",
                func=functools.partial(
                    self.snapshot_shape_data,
                ),
            )

        if option_name == "Save Shape Data File":
            return aniseed.widgets.ButtonWidget(
                button_name="Save Shape Data File",
                func=functools.partial(
                    self.save_shape_data_file,
                ),
            )

        if option_name == "Load Shape Data File":
            return aniseed.widgets.ButtonWidget(
                button_name="Load Shape Data File",
                func=functools.partial(
                    self.load_shape_file,
                ),
            )

        if option_name == "Clear Shape Data":
            return aniseed.widgets.ButtonWidget(
                button_name="Clear Shape Data",
                func=functools.partial(
                    self.clear_shape_data,
                ),
            )

        return None

    def run(self) -> bool:

        if not self.option("Apply Data").get():
            return True

        skip_nodes = self.option("Skip Nodes").get()
        stored_shape_data = self.option("Shape Data").get() or self.get_legacy_data()

        for shape_data in stored_shape_data:

            node = shape_data["node"]

            if not mc.objExists(node):
                continue

            if node in skip_nodes:
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
                        pass


        return True

    def clear_shape_data(self):
        confirmation = qtility.request.confirmation(
            title="Clear Shape Data",
            message="Are you sure you want to clear the shape data?",
        )
        if not confirmation:
            return

        self.option("Shape Data").set(dict())

    def snapshot_shape_data(self):
        data = self.get_shape_data()
        self.option("Shape Data").set(data)

    def save_shape_data_file(self):

        filepath = qtility.request.filepath(
            title="Save Shape Data File",
            path=os.path.dirname(mc.file(query=True, sceneName=True)),
            save=True,
        )

        if not filepath:
            return

        with open(filepath, "w") as f:
            print("shape data : %s" % self.get_shape_data())
            json.dump(self.get_shape_data(), f, sort_keys=True, indent=4)

    def load_shape_file(self):

        filepath = qtility.request.filepath(
            title="Load Shape Data File",
            path=os.path.dirname(mc.file(query=True, sceneName=True)),
            save=False,
        )

        if not filepath:
            return

        with open(filepath, "r") as f:
            self.option("Shape Data").set(json.load(f))

    def get_shape_data(self):

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

        return shape_data

    def get_legacy_data(self):

        stored_shape_data = list()

        # -- Find the store component so we can extract the data
        for component in self.rig.components():
            if isinstance(component, StoreControlShapes):
                option_name = "Shape Data"
                if component.option("Transient Shape Data").get():
                    option_name = "Transient Shape Data"
                stored_shape_data: list = component.option(option_name).get()

        return stored_shape_data
