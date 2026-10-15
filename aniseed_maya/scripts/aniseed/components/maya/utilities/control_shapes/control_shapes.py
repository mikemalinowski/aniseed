"""
Provides the control shape components. "Utility : Apply Control Shapes"
rebuilds rig controls' curve shapes from stored shape data (which can be
snapshotted, cleared, saved or loaded via buttons), preserving incoming
connections on the shapes. "Utility : Store Control Shapes" is a deprecated,
no-op holder of legacy shape data, and "Utility : Delete Shapes" removes all
shapes from a list of nodes.
"""
import os
import mref
import aniseed
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
        """
        Declares the legacy options (including the hidden Shape Data and
        Transient Shape Data stores) kept so existing rigs still load.
        """
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
        """
        Does nothing. The stored data is read by Apply Control Shapes.
        """
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
        """
        Declares the Apply Data and Skip Nodes options, the hidden Shape
        Data store, and button options to snapshot, clear, save and load
        that data.
        """
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
        """
        Returns an object list for Skip Nodes and a button widget for each
        of the snapshot, save, load and clear options, bound to the
        matching method.
        """
        if option_name == "Skip Nodes":
            return aniseed.widgets.ObjectList()

        # -- Each button option shares its name with its button label
        buttons = {
            "Snapshot Shape Data": self.snapshot_shape_data,
            "Save Shape Data File": self.save_shape_data_file,
            "Load Shape Data File": self.load_shape_file,
            "Clear Shape Data": self.clear_shape_data,
        }
        if option_name in buttons:
            return aniseed.widgets.ButtonWidget(
                button_name=option_name,
                func=buttons[option_name],
            )

        return None

    def run(self) -> bool:
        """
        Rebuilds the curve shapes of each stored control from Shape Data,
        falling back to data held by a Store Control Shapes component when
        Shape Data is empty. Missing and skipped nodes are ignored. Incoming
        connections to each shape are disconnected before the rebuild and
        reconnected to every new shape afterwards, with failures printed
        rather than raised. Does nothing if Apply Data is off.
        """

        if not self.option("Apply Data").get():
            return True

        skip_nodes = self.option("Skip Nodes").get()
        stored_shape_data = self.option("Shape Data").get() or self.read_stored_data()

        for shape_data in stored_shape_data:

            node = shape_data["node"]

            if not mref.objExists(node):
                continue

            if node in skip_nodes:
                continue

            # -- The connection juggling below works on raw plug strings with
            # -- maya.cmds deliberately: the connectAttr failures must be
            # -- caught (and reported) per connection, whereas mref's
            # -- connect swallows every error.
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

            for driving_attribute, destination_name in connection_pairs:
                for shape in cmds.listRelatives(node, shapes=True) or list():
                    destination_attribute = f"{shape}.{destination_name}"

                    try:
                        cmds.connectAttr(driving_attribute, destination_attribute)
                    except RuntimeError:
                        print(f"could not reconnect {driving_attribute} to {destination_attribute}")

        return True

    def clear_shape_data(self):
        """
        Empties the Shape Data option after asking the user to confirm.
        """
        aniseed_toolkit.option_files.clear_option(
            self.option("Shape Data"),
            title="Clear Shape Data",
            message="Are you sure you want to clear the shape data?",
            empty_value=dict(),
        )

    def snapshot_shape_data(self):
        """
        Stores the current shapes of this rig's controls in Shape Data.
        """
        self.option("Shape Data").set(self.get_shape_data())

    def save_shape_data_file(self):
        """
        Prompts for a file and saves a fresh snapshot of this rig's control
        shapes to it as JSON. Note that this captures the scene, not the
        stored Shape Data.
        """
        aniseed_toolkit.option_files.save_json_file(
            title="Save Shape Data File",
            get_data=self.get_shape_data,
        )

    def load_shape_file(self):
        """
        Prompts for a JSON file and loads its contents into Shape Data.
        """
        aniseed_toolkit.option_files.load_json_file(
            title="Load Shape Data File",
            option=self.option("Shape Data"),
        )

    def get_shape_data(self):
        """
        Returns the shape data of every control in the scene which belongs
        to this rig.
        """
        return [
            aniseed_toolkit.shapes.shape_to_dict(node)
            for node in aniseed_toolkit.control_queries.curve_controls()

            # -- Ensure we're only looking at controls which are part
            # -- of our rig
            if self.rig.label in mref.get(node).full_name()
        ]

    def read_stored_data(self):
        """
        Returns the shape data held by any (deprecated) Store Control Shapes
        component in the rig.
        """
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
        """
        Declares the Nodes input.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes that the attribute will be set on. Each node must already have the named attribute.",
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object list for the Nodes input.
        """
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()

    def run(self):
        """
        Deletes every shape node under each node in Nodes.
        """
        for node_name in self.input("Nodes").get():
            for shape in mref.get(node_name).shapes():
                mref.delete(shape)
