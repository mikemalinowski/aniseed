import mref
import aniseed
from maya import cmds


class RotationAxisReader(aniseed.RigComponent):
    """
    Builds a pose-reader mechanism that emits a 0-to-1 float attribute as a
    tracked transform rotates toward a captured target orientation. The
    reader places an org/rotator/tracker triplet alongside the tracked node
    and measures the distance from the tracker to a target node, mapping
    that distance to the pose attribute on the chosen Attribute Host.
    """

    identifier = "Utility : Rotation Axis Reader"

    rotate_order_enum = {
        "X": 0,
        "Y": 1,
        "Z": 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Transform To Track",
            value="",
            description="The transform whose rotation drives the pose value. The reader's attribute approaches 1.0 as this node rotates toward the captured target orientation.",
        )

        self.declare_input(
            name="Attribute Host",
            value="",
            description="The node on which the resulting 0-to-1 pose float attribute will be added.",
        )

        self.declare_option(
            name="Target Matrix",
            value=None,
            hidden=True,
            description="Internal storage for the captured target orientation, expressed as a local matrix relative to the org. Populated by the 'Set Target Transform' button.",
        )

        self.declare_option(
            name="Target Matrix Button",
            value=None,
            description="Press 'Set Target Transform' to capture the current pose of the tracker as the target. The pose attribute will read 1.0 when the tracker matches this captured orientation.",
        )

        self.declare_option(
            name="Prefix",
            value="",
            description="Used both as the name of the float attribute added to the Attribute Host and as a descriptive prefix for the generated mechanism nodes.",
        )

        self.declare_option(
            name="Location",
            value="md",
            description="The location token used when generating names for the mechanism nodes (e.g. 'lf', 'rt', 'md').",
        )

        self.declare_option(
            name="Axis",
            value="x",
            description="The local rotation axis to read on the tracked transform (X, Y or Z). Determines the tracker's translate direction and the rotator's rotateOrder.",
        )

        self.declare_option(
            name="Lock X",
            value=False,
            description="If true, rotation around X is skipped on the orientConstraint so it does not contribute to the pose value.",
        )
        self.declare_option(
            name="Lock Y",
            value=False,
            description="If true, rotation around Y is skipped on the orientConstraint so it does not contribute to the pose value.",
        )
        self.declare_option(
            name="Lock Z",
            value=False,
            description="If true, rotation around Z is skipped on the orientConstraint so it does not contribute to the pose value.",
        )

        self.declare_output(
            name="Org",
            description="The org transform that anchors the reader mechanism alongside the tracked transform.",
        )

        self.declare_output(
            name="Tracker",
            description="The transform that swings with the tracked node's rotation. Its distance to the (static) target node drives the pose value.",
        )

        self.declare_output(
            name="Attribute",
            description="The full path to the float pose attribute on the Attribute Host. Reads 0.0 at rest and 1.0 when the tracker matches the captured target orientation.",
        )

    def input_widget(self, requirement_name):
        """
        This allows us to provide dedicate widgets for specific inputs
        """
        if requirement_name in ["Transform To Track", "Attribute Host"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        if option_name == "Axis":
            return aniseed.widgets.AxisSelector()

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name == "Target Matrix Button":
            return aniseed.widgets.ButtonWidget(
                button_name="Set Target Transform",
                func=self.user_func_set_target,
            )

    def run(self):

        transform_to_track = mref.get(self.input("Transform To Track").get())
        host = mref.get(self.input("Attribute Host").get())
        prefix = self.option("Prefix").get()
        location = self.option("Location").get()
        axis = self.option("Axis").get().upper()
        target_matrix = self.option("Target Matrix").get()

        lock_x = self.option("Lock X").get()
        lock_y = self.option("Lock Y").get()
        lock_z = self.option("Lock Z").get()

        pose_attribute = host.add_attribute(
            prefix,
            value=0,
            attribute_type="float",
            keyable=False,
        )

        org = mref.create(
            "transform",
            name=self.config.generate_name(
                classification="org",
                description=f"{prefix}PoseReader",
                location=location,
            ),
            parent=transform_to_track.parent(),
        )
        org.set_parent(transform_to_track.parent())
        org.match_to(transform_to_track)

        rotator = mref.create(
            "transform",
            name=self.config.generate_name(
                classification="mech",
                description=f"{prefix}PoseReaderRotator",
                location=location,
            ),
            parent=org.full_name(),
        )
        rotator.match_to(transform_to_track)
        rotator.attr("rotateOrder").set(self.rotate_order_enum[axis])

        # -- Create the tracker, this is the node that will move around
        tracker = mref.create(
            "transform",
            name=self.config.generate_name(
                classification="mech",
                description=f"{prefix}PoseReaderTracker",
                location=location,
            ),
            parent=rotator.full_name(),
        )
        tracker.match_to(rotator)
        tracker.attr(f"translate{axis}").set(1)

        # -- Determine which axis we need to skip
        skip_axis = []
        if lock_x:
            skip_axis.append("x")

        if lock_y:
            skip_axis.append("y")

        if lock_z:
            skip_axis.append("z")

        cmds.orientConstraint(
            transform_to_track.full_name(),
            rotator.full_name(),
            maintainOffset=True,
            skip=skip_axis,
        )

        # -- Now we need to create our target
        target = mref.create(
            "transform",
            name=self.config.generate_name(
                classification="mech",
                description=f"{prefix}PoseReaderTarget",
                location=location,
            ),
            parent=transform_to_track.full_name(),
        )
        target.set_matrix(target_matrix or tracker.get_matrix())
        target.set_parent(org.full_name())

        # -- Now create the distance node
        distance_node = mref.create(
            "distanceBetween",
            name=self.config.generate_name(
                classification="mech",
                description=f"{prefix}PoseReaderDistance",
                location=location,
            ),
        )
        tracker.attr("worldMatrix[0]").connect(distance_node.attr("inMatrix1"))
        target.attr("worldMatrix[0]").connect(distance_node.attr("inMatrix2"))

        # -- Range the node such that we get a zero to one value
        range_node = mref.create(
            "setRange",
            name=self.config.generate_name(
                classification="mech",
                description=f"{prefix}PoseReaderRange",
                location=location,
            ),
        )
        range_node.attr("minX").set(0)
        range_node.attr("maxX").set(1)
        range_node.attr("oldMinX").set(0)
        range_node.attr("oldMaxX").set(distance_node.attr("distance").get())
        distance_node.attr("distance").connect(range_node.attr("valueX"))

        # -- Next we need to reverse it, so we get a 1 value when we're
        # -- at the transform location (i.e, the distance is zero)
        reverse_node = mref.create(
            "reverse",
            name=self.config.generate_name(
                classification="mech",
                description=f"{prefix}PoseReaderReverse",
                location=location,
            ),
        )
        range_node.attr("outValueX").connect(reverse_node.attr("inputX"))
        reverse_node.attr("outputX").connect(pose_attribute)

        self.output("Tracker").set(tracker.full_name())
        self.output("Attribute").set(pose_attribute.path())
        self.output("Org").set(org.full_name())

    def user_func_set_target(self):
        org = mref.get(self.output("Org").get())
        tracker = mref.get(self.output("Tracker").get())

        temp_node = mref.create("transform", parent=org.full_name())
        temp_node.match_to(tracker)

        self.option("Target Matrix").set(temp_node.get_matrix())
        cmds.delete(temp_node.full_name())
