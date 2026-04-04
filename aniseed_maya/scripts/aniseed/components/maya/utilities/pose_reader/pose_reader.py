import mref
import aniseed
from maya import cmds


class RotationAxisReader(aniseed.RigComponent):

    identifier = "Utility : Rotation Axis Reader"

    rotate_order_enum = {
        "X": 0,
        "Y": 1,
        "Z": 2,
    }

    def __init__(self, *args, **kwargs):
        super(RotationAxisReader, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Transform To Track",
            value="",
        )

        self.declare_input(
            name="Attribute Host",
            value="",
        )

        self.declare_option(
            name="Target Matrix",
            value=None,
            hidden=True,
        )

        self.declare_option(
            name="Target Matrix Button",
            value=None,
        )

        self.declare_option(
            name="Prefix",
            value="",
        )

        self.declare_option(
            name="Location",
            value="md",
        )

        self.declare_option(
            name="Axis",
            value="x",
        )

        self.declare_option(
            name="Lock X",
            value=False,
        )
        self.declare_option(
            name="Lock Y",
            value=False,
        )
        self.declare_option(
            name="Lock Z",
            value=False,
        )

        self.declare_output(
            name="Org",
        )

        self.declare_output(
            name="Tracker",
        )

        self.declare_output(
            name="Attribute",
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
        rotator.attr("rotateOrder").set(self.rotate_order_enum[axis.upper()])

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
        distance_node = mref.create("distanceBetween")
        tracker.attr("worldMatrix[0]").connect(distance_node.attr("inMatrix1"))
        target.attr("worldMatrix[0]").connect(distance_node.attr("inMatrix2"))

        # -- Range the node such that we get a zero to one value
        range_node = mref.create("setRange")
        range_node.attr("minX").set(0)
        range_node.attr("maxX").set(1)
        range_node.attr("oldMinX").set(0)
        range_node.attr("oldMaxX").set(distance_node.attr("distance").get())
        distance_node.attr("distance").connect(range_node.attr("valueX"))

        # -- Next we need to reverse it, so we get a 1 value when we're
        # -- at the transform location (i.e, the distance is zero)
        reverse_node = mref.create("reverse")
        range_node.attr("outValueX").connect(reverse_node.attr("inputX"))
        reverse_node.attr("outputX").connect(pose_attribute)

        self.output("Tracker").set(tracker.full_name())
        self.output("Attribute").set(pose_attribute.path())
        self.output("Org").set(org.full_name())

    def user_func_set_target(self):
        transform_to_track = mref.get(self.output("Org").get())
        tracker = mref.get(self.output("Tracker").get())

        temp_node = mref.create("transform", parent=transform_to_track.full_name())
        temp_node.match_to(tracker)

        self.option("Target Matrix").set(temp_node.get_matrix())
        cmds.delete(temp_node.full_name())
