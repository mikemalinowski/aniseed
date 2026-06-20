import os
import mref
import json
import aniseed
import qtility
import functools
import aniseed_toolkit

from maya import cmds


# noinspection PyUnresolvedReferences
class StoreControlShapes(aniseed.RigComponent):
    """
    Deprecated : Do not continue to use this component. The Apply Shape Data component
    now has functionality to snapshot and hold the shape data it applies.
    """
    identifier = "Utility : Store Control Shapes"
    icon = os.path.join(os.path.dirname(__file__), "store_shapes.png")

    deprecated = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Store Data",
            value=True,
            description="Legacy toggle. Kept for backwards compatibility with existing rigs.",
        )

        self.declare_option(
            name="Shape Data",
            value=list(),
            hidden=True,
            description="Persistent snapshot of control shapes. Populated by older workflows; superseded by Apply Control Shapes.",
        )

        self.declare_option(
            name="Transient Shape Data",
            value=list(),
            hidden=True,
            description="One-build-only snapshot of control shapes. Takes precedence over Shape Data when both are populated.",
        )

        self.declare_option(
            name="_Clear Shapes",
            value=None,
            description="Legacy clear-shapes action. Kept for backwards compatibility with existing rigs.",
        )

    def run(self) -> bool:
        return True


# noinspection PyUnresolvedReferences
class ApplyControlShapes(aniseed.RigComponent):
    """
    Applies persisted curve-shape data to every controller in the rig.
    The shape data can be snapshotted from the current scene, cleared,
    saved to / loaded from a JSON file, or supplied by an upstream
    StoreControlShapes component. Existing input connections on each
    shape's attributes are preserved across the rebuild.
    """

    identifier = "Utility : Apply Control Shapes"
    icon = os.path.join(os.path.dirname(__file__), "apply_shapes.png")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Apply Data",
            value=True,
            description="If false, the component is a no-op. Useful for temporarily disabling shape application without removing the component.",
        )

        self.declare_option(
            name="Skip Nodes",
            value=list(),
            hidden=False,
            description="Nodes that should be left untouched even if their data is present in Shape Data.",
        )

        self.declare_option(
            name="Shape Data",
            value=list(),
            hidden=True,
            description="The persisted shape data applied to controls at build time. Populated via Snapshot Shape Data, Load Shape Data File, or an upstream Store Control Shapes component.",
        )

        self.declare_option(
            name="Snapshot Shape Data",
            value=None,
            description="Button. Captures the curve shapes of every rig controller currently in the scene and stores them in Shape Data.",
        )

        self.declare_option(
            name="Clear Shape Data",
            value=None,
            description="Button. Empties the Shape Data store after confirmation.",
        )

        self.declare_option(
            name="Save Shape Data File",
            value=None,
            description="Button. Writes the current snapshot to a JSON file on disk.",
        )

        self.declare_option(
            name="Load Shape Data File",
            value=None,
            description="Button. Replaces Shape Data with the contents of a JSON file on disk.",
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
        stored_shape_data = self.option("Shape Data").get() or self.read_stored_data()

        for shape_data in stored_shape_data:

            node = shape_data["node"]

            if not cmds.objExists(node):
                continue

            if node in skip_nodes:
                continue
            
            connection_pairs = []
            for shape in cmds.listRelatives(node, shapes=True) or list():
                connection_data = cmds.listConnections(
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
                    cmds.disconnectAttr(driving_attribute, f"{shape}.{destination_attribute}")

            aniseed_toolkit.shapes.load_shape(
                node=node,
                data=shape_data,
                clear=True,
                color=None,
                scale_by=1,
            )

            for connection_pair in connection_pairs:
                for shape in cmds.listRelatives(node, shapes=True) or list():
                    driving_attribute = connection_pair[0]
                    destination_attribute = f"{shape}.{connection_pair[1]}"

                    try:
                        cmds.connectAttr(driving_attribute, destination_attribute)
                    except RuntimeError:
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
            path=os.path.dirname(cmds.file(query=True, sceneName=True)),
            save=True,
        )

        if not filepath:
            return

        shape_data = self.get_shape_data()

        with open(filepath, "w") as f:
            json.dump(shape_data, f, sort_keys=True, indent=4)

    def load_shape_file(self):

        filepath = qtility.request.filepath(
            title="Load Shape Data File",
            path=os.path.dirname(cmds.file(query=True, sceneName=True)),
            save=False,
        )

        if not filepath:
            return

        with open(filepath, "r") as f:
            self.option("Shape Data").set(json.load(f))

    def get_shape_data(self):

        nodes = cmds.controller(
            allControllers=True,
            query=True,
        )

        shape_data = list()

        for node in nodes:

            # -- Ensure we're only looking at controls which are part
            # -- of our rig
            if not self.rig.label in cmds.ls(node, long=True)[0]:
                continue

            shape_nodes = cmds.listRelatives(node, type="nurbsCurve")

            if not shape_nodes:
                continue

            shape_data.append(
                aniseed_toolkit.shapes.shape_to_dict(node),
            )

        return shape_data

    def read_stored_data(self):

        stored_shape_data = list()

        # -- Find the store component so we can extract the data
        for component in self.rig.components():
            if isinstance(component, StoreControlShapes):
                option_name = "Shape Data"
                if component.option("Transient Shape Data").get():
                    option_name = "Transient Shape Data"
                stored_shape_data: list = component.option(option_name).get()

        return stored_shape_data


# noinspection PyUnresolvedReferences
class DeleteShapes(aniseed.RigComponent):
    """
    Removes all the shapes from a node
    """


    identifier = "Utility : Delete Shapes"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes that the attribute will be set on. Each node must already have the named attribute.",
        )


    def input_widget(self, requirement_name: str):
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()

    def run(self):
        node_names = self.input("Nodes").get()

        for node_name in node_names:
            node = mref.get(node_name)

            for shape in node.shapes():
                mref.delete(shape)
