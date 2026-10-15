"""
Provides the "Limb : Eye" component, which builds an aimed eye control with
optional eye lid follow, blink and pupil behaviour, and the "Limb : Eyes"
component, which builds a left and right eye through two internal Eye
components and adds a central master aim control parenting both eye aims.
Both can generate their joints when added to the stack.
"""
import os
import mref
import typing
import aniseed
import aniseed_toolkit
from maya import cmds


# -- The labels used to prefix the side specific inputs of the eyes component
SIDES = ["Left", "Right"]

# -- The inputs of the single eye component which are exposed per side
# -- on the eyes component
SIDE_INPUTS = [
    "Eye Joint",
    "Lower Eye Lid Joint",
    "Upper Eye Lid Joint",
    "Pupil Joint",
]


def get_cross_axis(forward_axis: str, up_axis: str) -> str:
    """
    Returns the axis (X, Y or Z) which is neither the forward nor the up axis
    """
    all_axis = ["X", "Y", "Z"]
    all_axis.remove(forward_axis)
    all_axis.remove(up_axis)
    return all_axis[0]


class EyesComponent(aniseed.RigComponent):
    """
    This component adds a left and right eye
    """

    identifier = "Limb : Eyes"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent input plus left and right eye, eye lid and pupil
        joint inputs, the options which are passed through to the two single
        eye components (aim distance, blink, pupil, axes, lid follow defaults)
        and per side control outputs plus the central aim control and org.
        """
        super(EyesComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig"
        )

        self.declare_input(
            name="Left Eye Joint",
            value="",
            group="Required Joints (Left)"
        )
        self.declare_input(
            name="Left Upper Eye Lid Joint",
            value="",
            validate=False,
            group="Required Joints (Left)"
        )

        self.declare_input(
            name="Left Lower Eye Lid Joint",
            value="",
            validate=False,
            group="Required Joints (Left)"
        )

        self.declare_input(
            name="Right Eye Joint",
            value="",
            group="Required Joints (Right)"
        )

        self.declare_input(
            name="Right Upper Eye Lid Joint",
            value="",
            validate=False,
            group="Required Joints (Right)"
        )

        self.declare_input(
            name="Right Lower Eye Lid Joint",
            value="",
            validate=False,
            group="Required Joints (Right)"
        )

        self.declare_input(
            name="Left Pupil Joint",
            value="",
            validate=False,
            group="Optional Joints",
        )

        self.declare_input(
            name="Right Pupil Joint",
            value="",
            validate=False,
            group="Optional Joints",
        )


        self.declare_option(
            name="Name",
            value="Eye",
            group="Naming",
        )

        self.declare_option(
            name="Align Controls To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Master Control To World",
            value=True,
            group="Behaviour",
        )


        self.declare_option(
            name="Aim Distance",
            value=aniseed_toolkit.units.to_cm(30),
            group="Behaviour",
        )

        self.declare_option(
            name="Add Blink",
            value=True,
            group="Behaviour",
        )


        self.declare_option(
            name="Auto Blink Upper Multiplier",
            value=1,
            group="Behaviour",
        )

        self.declare_option(
            name="Auto Blink Lower Multiplier",
            value=1,
            group="Behaviour",
        )

        self.declare_option(
            name="Add Pupil",
            value=False,
            group="Behaviour",
            pre_expose=True,
        )

        self.declare_option(
            name="Forward Axis",
            value="Z",
            group="Behaviour",
        )

        self.declare_option(
            name="Up Axis",
            value="Y",
            group="Behaviour",
        )

        self.declare_option(
            name="Include Eye Lids",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Default Upper Lid Follow",
            value=0.5,
            group="Defaults",
        )

        self.declare_option(
            name="Default Lower Lid Follow",
            value=0.1,
            group="Defaults",
        )

        self.declare_option(
            name="Default Horizontal Follow",
            value=0.2,
            group="Defaults",
        )

        self.declare_option(
            name="Max Blink Rotation",
            value=65,
            group="Defaults",
        )

        self.declare_output(
            name="Left Eye Control",
        )

        self.declare_output(
            name="Left Aim Control",
        )

        self.declare_output(
            name="Right Eye Control",
        )

        self.declare_output(
            name="Right Aim Control",
        )

        self.declare_output(
            name="Central Aim Control",
        )

        self.declare_output(
            name="Left Upper Eye Lid Control",
        )
        self.declare_output(
            name="Left Lower Eye Lid Control",
        )
        self.declare_output(
            name="Right Upper Eye Lid Control",
        )
        self.declare_output(
            name="Right Lower Eye Lid Control",
        )
        self.declare_output(
            name="Left Pupil Control",
        )
        self.declare_output(
            name="Right Pupil Control",
        )
        self.declare_output(
            name="org"
        )

    def on_enter_stack(self):
        """
        Creates the left and right eye joints under the current selection and
        then attempts to hook the parent input to the parent component.
        """
        self.user_func_create_skeleton()
        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for every input.
        """
        # -- Note: every input is given an object selector (this previously
        # -- iterated a list of input names but always returned on the
        # -- first iteration, regardless of the requirement name)
        return aniseed.widgets.ObjectSelector(component=self)

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Exposes a "Create Joints" menu entry when no left eye joint is set.
        """
        menu = super(EyesComponent, self).user_functions()

        if not self.input("Left Eye Joint").get():
            menu["Create Joints"] = self.user_func_create_skeleton

        return menu

    def run(self):
        """
        Builds a left and right single eye component under an eyes org, then
        creates a master aim control placed between the two eye aims which
        parents them both. The per side outputs are copied from the sub
        components.
        """
        parent = mref.get(self.input("Parent").get())
        org = mref.create(
            "transform",
            name=self.config.generate_name(
                classification="org",
                description="eyes",
                location=self.config.middle,
            ),
            parent=parent,
        )
        org.match_to(parent)
        self.output("org").set(org.name())

        lf_eye_component, rt_eye_component = self._get_components(parent=org.name())

        lf_eye_component.run()
        rt_eye_component.run()

        aim_controls = [
            aniseed_toolkit.control.get(eye_component.output("Aim Control").get())
            for eye_component in [lf_eye_component, rt_eye_component]
        ]

        # -- Create the control to act as the master aim
        master_aim_control = aniseed_toolkit.control.create(
            description=f"{self.option('Name').get()}AimMaster",
            location=self.config.middle,
            config=self.config,
            shape="core_sphere",
            parent=self.input("Parent").get(),
            match_to=lf_eye_component.output("Aim Control").get(),
        )
        master_aim_org = mref.get(master_aim_control.org)

        # -- Align the controls if we need to
        if self.option("Align Master Control To World").get():
            master_aim_org.set_rotation([0, 0, 0], space="world")

        # -- Place the master aim between the two eye aims and make it
        # -- their parent
        ws_left, ws_right = [
            mref.get(aim_control.ctl).get_position(space="world")
            for aim_control in aim_controls
        ]

        master_aim_org.set_position(
            [
                (ws_left[axis] + ws_right[axis]) * 0.5
                for axis in range(3)
            ],
            space="world",
        )

        for aim_control in aim_controls:
            mref.get(aim_control.org).set_parent(master_aim_control.ctl)

        # -- Set all our outputs
        side_outputs = [
            "Eye Control",
            "Aim Control",
            "Upper Eye Lid Control",
            "Lower Eye Lid Control",
            "Pupil Control",
        ]
        for side, eye_component in [("Left", lf_eye_component), ("Right", rt_eye_component)]:
            for output_name in side_outputs:
                self.output(f"{side} {output_name}").set(eye_component.output(output_name).get())

        self.output("Central Aim Control").set(master_aim_control.ctl)

    def _get_components(self, parent=None):
        """
        Creates the left and right EyeComponent instances (not added to the
        stack), copying across any matching inputs and options, the side
        specific joint inputs and the side location.

        Args:
            parent: Optional node to set as the parent input of both eyes

        Returns:
            A list of the left and right eye components
        """

        # -- Create the two individual eye components
        lf_eye_component = EyeComponent(label="lf", stack=self.stack)
        rt_eye_component = EyeComponent(label="rt", stack=self.stack)

        components = [
            lf_eye_component,
            rt_eye_component,
        ]

        # -- Deal with the shared requirements and options
        for component in components:
            for input_ in self.inputs():
                if component.input(input_.name()):
                    component.input(input_.name()).set(
                        input_.get(),
                    )

            for option in self.options():
                if component.option(option.name()):
                    component.option(option.name()).set(
                        option.get(),
                    )

        if parent:
            lf_eye_component.input("Parent").set(parent)
            rt_eye_component.input("Parent").set(parent)

        # -- Now set the side specific requirements
        for side, component in zip(SIDES, components):
            for input_name in SIDE_INPUTS:
                component.input(input_name).set(
                    self.input(f"{side} {input_name}").get(),
                )

        lf_eye_component.option("Location").set(
            self.config.left,
        )

        rt_eye_component.option("Location").set(
            self.config.right,
        )

        return components

    def user_func_create_skeleton(self):
        """
        Creates the joints for both eyes using the single eye components,
        snapping them to the first selected node (which must exist), offsetting
        them to either side and parenting them to it. The side specific inputs
        are then populated with the created joints.
        """

        parent = mref.selected()[0]

        cross_axis = get_cross_axis(
            self.option("Forward Axis").get(),
            self.option("Up Axis").get(),
        )

        # -- Note: the eyes are only offset from each other when the cross
        # -- axis is X. For any other cross axis they are left at the
        # -- parent position (preserved behaviour).
        side_offset = 0
        if cross_axis == "X":
            side_offset = self.option("Aim Distance").get() * 0.2

        for side, multiplier, component in zip(SIDES, [1, -1], self._get_components()):

            # -- Clear the selection so the eye joints are not parented to it
            # -- (mref.select has no clear option)
            cmds.select(clear=True)

            root_joint = component.user_func_create_skeleton()

            aniseed_toolkit.transformation.snap_position(root_joint, parent.full_name())
            mref.get(root_joint).attr(f"translate{cross_axis}").set(side_offset * multiplier)

            # -- Now set the side specific requirements
            for input_name in SIDE_INPUTS:
                self.input(f"{side} {input_name}").set(
                    component.input(input_name).get(),
                )

            mref.get(root_joint).set_parent(parent)


class EyeComponent(aniseed.RigComponent):
    """
    This is a single eye component
    """
    identifier = "Limb : Eye"

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, eye joint and optional eye lid and pupil joint
        inputs, the naming, aim, axis, blink and lid follow options and the
        eye, aim, eye lid and pupil control outputs.
        """
        super(EyeComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig"
        )

        self.declare_input(
            name="Eye Joint",
            value="",
            group="Required Joints"
        )

        self.declare_input(
            name="Upper Eye Lid Joint",
            value="",
            validate=False,
            group="Optional Joints",
        )

        self.declare_input(
            name="Lower Eye Lid Joint",
            value="",
            validate=False,
            group="Optional Joints",
        )

        self.declare_input(
            name="Pupil Joint",
            value="",
            validate=False,
            group="Optional Joints",
        )

        self.declare_option(
            name="Name",
            value="Eye",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="lf",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Align Controls To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Aim Distance",
            value=aniseed_toolkit.units.to_cm(30),
            group="Behaviour",
        )

        self.declare_option(
            name="Forward Axis",
            value="X",
            group="Behaviour",
        )

        self.declare_option(
            name="Up Axis",
            value="Y",
            group="Behaviour",
        )

        self.declare_option(
            name="Include Eye Lids",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Add Pupil",
            value=False,
            group="Behaviour",
            pre_expose=True,
        )


        self.declare_option(
            name="Add Blink",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Auto Blink Upper Multiplier",
            value=1,
            group="Behaviour",
        )

        self.declare_option(
            name="Auto Blink Lower Multiplier",
            value=1,
            group="Behaviour",
        )

        self.declare_option(
            name="Default Upper Lid Follow",
            value=0.5,
            group="Defaults",
        )

        self.declare_option(
            name="Default Lower Lid Follow",
            value=0.1,
            group="Defaults",
        )

        self.declare_option(
            name="Default Horizontal Follow",
            value=0.2,
            group="Defaults",
        )


        self.declare_option(
            name="Max Blink Rotation",
            value=65,
            group="Defaults",
        )

        self.declare_output(
            name="Eye Control",
        )

        self.declare_output(
            name="Aim Control",
        )

        self.declare_output(
            name="Upper Eye Lid Control",
        )
        self.declare_output(
            name="Lower Eye Lid Control",
        )
        self.declare_output(
            name="Pupil Control",
        )

    def on_enter_stack(self):
        """
        Creates the eye joints under the current selection.
        """
        self.user_func_create_skeleton()

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the parent and eye joint inputs. Note
        that the eye lid names checked here ("Upper Eyelid Joint") do not
        match the declared inputs, so the lid inputs get no widget.
        """

        object_requirements = [
            "Parent",
            "Eye Joint",
            "Upper Eyelid Joint",
            "Lower Eyelid Joint",
        ]

        if requirement_name in object_requirements:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        """
        Returns a location selector for the Location option and an axis
        selector for the Forward Axis and Up Axis options.
        """

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name in ["Forward Axis", "Up Axis"]:
            return aniseed.widgets.AxisSelector()

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Exposes a "Create Joints" menu entry when no eye joint is set. When
        the eye joint is set this returns None rather than the menu.
        """
        menu = super(EyeComponent, self).user_functions()

        if not self.input("Eye Joint").get():
            menu["Create Joints"] = self.user_func_create_skeleton
            return menu

        # -- Note: when the eye joint is set no menu is returned (preserved
        # -- behaviour)

    def user_func_create_skeleton(self):
        """
        Creates the eye joint under the first selected node, along with lower
        and upper lid joints (if Include Eye Lids is on) and a pupil joint (if
        Add Pupil is on), and sets the corresponding inputs.

        Returns:
            The created eye joint
        """

        # -- Determine the parent for the joints
        parent = aniseed_toolkit.mutils.first_selected()

        description = self.option("Name").get()
        location = self.option("Location").get()

        # -- Start by creating the eye
        eye_joint = aniseed_toolkit.joints.create(
            description=description,
            location=location,
            parent=parent,
            config=self.config,
        )
        self.input("Eye Joint").set(eye_joint)

        if self.option("Include Eye Lids").get():
            # -- Now create the eyelids
            for label in ["Lower", "Upper"]:

                lid_joint = aniseed_toolkit.joints.create(
                    description=f"{description}{label}Lid",
                    location=location,
                    parent=eye_joint,
                    config=self.config,
                )
                self.input(f"{label} Eye Lid Joint").set(lid_joint)

        if self.option("Add Pupil").get():
            pupil_joint = aniseed_toolkit.joints.create(
                description=f"{description}Pupil",
                location=location,
                parent=eye_joint,
                config=self.config,
            )
            self.input("Pupil Joint").set(pupil_joint)

        if parent:
            aniseed_toolkit.transformation.snap_position(eye_joint, parent)

        return eye_joint

    def run(self):
        """
        Builds the eye control and an aim control pushed out along the forward
        axis. An aim constraint (stabilised by an upvector) drives the eye
        control, which in turn drives the eye joint. Eye lids, blink and pupil
        behaviour are added depending on the options.
        """

        eye_joint = self.input("Eye Joint").get()

        description = self.option("Name").get()
        location = self.option("Location").get()

        forward_axis = self.option("Forward Axis").get()
        up_axis = self.option("Up Axis").get()

        # -- Create a node to place everything under
        component_org = aniseed_toolkit.transforms.create(
            classification=self.config.organisational,
            description=description + "Component",
            location=location,
            parent=self.input("Parent").get(),
            config=self.config,
        )

        # -- Create our eye control
        direct_eye_control = aniseed_toolkit.control.create(
            description=description,
            location=location,
            parent=component_org,
            match_to=eye_joint,
            config=self.config,
            shape="core_sphere",
        )

        # -- Create our aim control and move it to the right place
        aim_control = aniseed_toolkit.control.create(
            description=f"{description}Aim",
            location=location,
            parent=direct_eye_control.ctl,
            match_to=eye_joint,
            shape="core_sphere",
            config=self.config,
        )
        self.output("Eye Control").set(direct_eye_control.ctl)
        self.output("Aim Control").set(aim_control.ctl)

        # -- Create the guide line
        aniseed_toolkit.guide.link(
            aim_control.ctl,
            direct_eye_control.ctl,
        )

        aim_org = mref.get(aim_control.org)
        aim_org.attr(f"translate{forward_axis}").set(self.option("Aim Distance").get())

        # -- Parent the aim to be a child of the component org
        aim_org.set_parent(component_org)

        # -- Align the controls if we need to
        if self.option("Align Controls To World").get():
            mref.get(direct_eye_control.org).set_rotation([0, 0, 0], space="world")
            aim_org.set_rotation([0, 0, 0], space="world")

        # -- Create the upvector
        upvector = mref.get(
            aniseed_toolkit.transforms.create(
                classification="upv",
                description=description + "AimStabilizer",
                location=location,
                config=self.config,
                match_to=direct_eye_control.ctl,
                parent=direct_eye_control.ctl,
            ),
        )
        upvector.attr(f"translate{up_axis}").set(10)
        upvector.set_parent(component_org)

        # -- Create the aim setup
        aim_node = aniseed_toolkit.transforms.create(
            classification="aim",
            description=description,
            location=location,
            config=self.config,
            parent=component_org,
            match_to=direct_eye_control.ctl,
        )

        mref.aimConstraint(
            aim_control.ctl,
            aim_node,
            worldUpType="object",
            worldUpObject=upvector,
            aimVector=self.axis_vector(forward_axis),
            upVector=self.axis_vector(up_axis),
            maintainOffset=False,
        )

        # -- Constrain the joint
        mref.parentConstraint(
            aim_node,
            direct_eye_control.org,
            maintainOffset=True,
        )

        aniseed_toolkit.constraints.parent_and_scale(
            direct_eye_control.ctl,
            eye_joint,
        )

        if self.option("Include Eye Lids").get():
            lid_controls = self.create_eyelid_behaviour(
                component_org=component_org,
                eye_control=direct_eye_control.ctl,
                aim_control=aim_control.ctl,
            )

            if self.option("Add Blink").get():
                self.create_blink_behaviour(
                    eye_control=direct_eye_control,
                    upper_lid_control=lid_controls[1],
                    lower_lid_control=lid_controls[0],
                )

        if self.option("Add Pupil").get():
            self.create_pupil_behaviour(direct_eye_control)

    def create_blink_behaviour(self, eye_control, upper_lid_control, lower_lid_control):
        """
        Adds a blink attribute to the eye control which rotates the upper
        and lower lid controls closed.
        """
        node_math = aniseed_toolkit.rigging.node_math

        host = mref.get(eye_control.ctl)
        blink_attribute = host.add_attribute(
            "blink",
            value=0,
            attribute_type="float",
            keyable=True,
            min=0,
            max=1,
        )
        blink_reverse = node_math.multiply(blink_attribute.full_name(), -1)

        max_rotation = self.option("Max Blink Rotation").get()
        upper_rotation_multiplier = max_rotation * self.option("Auto Blink Upper Multiplier").get()
        lower_rotation_multiplier = max_rotation * self.option("Auto Blink Lower Multiplier").get()

        upper_rotation = node_math.multiply(blink_attribute.full_name(), upper_rotation_multiplier)
        lower_rotation = node_math.multiply(blink_reverse, lower_rotation_multiplier)

        mref.get(upper_rotation).connect(mref.get(upper_lid_control.zero).rotateX)
        mref.get(lower_rotation).connect(mref.get(lower_lid_control.zero).rotateX)

    def create_pupil_behaviour(self, eye_control):
        """
        Creates the pupil control along with a pupil scale attribute on the
        eye control
        """
        eye_controller = mref.get(eye_control.ctl)
        pupil_joint = self.input("Pupil Joint").get()

        pupil_control = aniseed_toolkit.control.create(
            description=f"{self.option('Name').get()}Pupil",
            location=self.option("Location").get(),
            config=self.config,
            parent=eye_controller.name(),
            shape="core_circle",
            match_to=pupil_joint,
        )
        aniseed_toolkit.constraints.parent_and_scale(
            pupil_control.ctl,
            pupil_joint,
            maintain_offset=False,
        )

        # -- Add the pupil scale attribute
        pupil_attribute = eye_controller.add_attribute(
            "pupil_scale",
            attribute_type="float",
            keyable=True,
            value=1,
        )
        for axis in ["X", "Y", "Z"]:
            pupil_attribute.connect(f"{pupil_control.zero}.scale{axis}")

        self.output("Pupil Control").set(pupil_control.ctl)

    def create_eyelid_behaviour(self, component_org, eye_control, aim_control):
        """
        Creates the eye lid controls, which follow the eye rotation by an
        amount driven by attributes on the eye control (and proxied onto
        the aim control).

        Returns:
            The lower and upper lid controls
        """
        description = self.option("Name").get()
        location = self.option("Location").get()

        forward_axis = self.option("Forward Axis").get()
        up_axis = self.option("Up Axis").get()
        cross_axis = get_cross_axis(forward_axis, up_axis)

        eye_controller = mref.get(eye_control)
        aim_controller = mref.get(aim_control)

        aniseed_toolkit.attributes.add_separator(eye_control)
        aniseed_toolkit.attributes.add_separator(aim_control)

        # -- Add the attribute we will use to blend the behaviour out
        auto_eyelids = eye_controller.add_attribute(
            "autoEyelids",
            value=None,
            attribute_type="float",
            defaultValue=1,
            keyable=True,
        )
        aniseed_toolkit.attributes.add_separator(eye_control)

        # -- Add the follow attributes, which are proxied onto the aim control
        follow_attributes = dict()
        for attribute_name, option_name in [
            ("upperLidFollow", "Default Upper Lid Follow"),
            ("lowerLidFollow", "Default Lower Lid Follow"),
            ("horizontalLidFollow", "Default Horizontal Follow"),
        ]:
            follow_attributes[attribute_name] = eye_controller.add_attribute(
                attribute_name,
                value=None,
                attribute_type="float",
                defaultValue=self.option(option_name).get(),
                keyable=True,
            )
            aim_controller.add_proxy(attribute_name, follow_attributes[attribute_name])

        vertical_multipliers = {
            "Lower": follow_attributes["lowerLidFollow"],
            "Upper": follow_attributes["upperLidFollow"],
        }

        lid_controls = []
        for label in ["Lower", "Upper"]:

            eye_lid_joint = self.input(f"{label} Eye Lid Joint").get()

            lid_driver_parent = aniseed_toolkit.transforms.create(
                classification="zro",
                description=f"{description}{label}LidDriver",
                location=location,
                parent=component_org,
                config=self.config,
                match_to=eye_lid_joint,
            )

            lid_driver = aniseed_toolkit.transforms.create(
                classification="mech",
                description=f"{description}{label}LidDriver",
                location=location,
                config=self.config,
                parent=lid_driver_parent,
                match_to=eye_lid_joint,
            )

            lid_tracker = aniseed_toolkit.transforms.create(
                classification="mech",
                description=f"{description}{label}LidTracker",
                location=location,
                config=self.config,
                parent=lid_driver_parent,
                match_to=eye_lid_joint,
            )

            mref.parentConstraint(
                eye_control,
                lid_tracker,
                maintainOffset=True,
            )

            # -- Scale the tracked rotation by the follow amounts, then scale
            # -- that by the auto eyelids blend before driving the lid
            m_lid_tracker = mref.get(lid_tracker)
            m_lid_driver = mref.get(lid_driver)

            horizontal_rotation = aniseed_toolkit.rigging.node_math.multiply(
                m_lid_tracker.attr(f"rotate{up_axis}").full_name(),
                follow_attributes["horizontalLidFollow"].full_name(),
            )
            vertical_rotation = aniseed_toolkit.rigging.node_math.multiply(
                m_lid_tracker.attr(f"rotate{cross_axis}").full_name(),
                vertical_multipliers[label].full_name(),
            )
            blend_multiplier = mref.create("multiplyDivide")

            mref.get(horizontal_rotation).connect(blend_multiplier.input1X)
            mref.get(vertical_rotation).connect(blend_multiplier.input1Y)
            auto_eyelids.connect(blend_multiplier.input2X)
            auto_eyelids.connect(blend_multiplier.input2Y)

            blend_multiplier.outputX.connect(m_lid_driver.attr(f"rotate{up_axis}"))
            blend_multiplier.outputY.connect(m_lid_driver.attr(f"rotate{cross_axis}"))

            lid_control = aniseed_toolkit.control.create(
                description=f"{label}EyeLid",
                location=location,
                parent=lid_driver,
                match_to=lid_driver,
                config=self.config,
                shape="core_cube",
            )
            lid_controls.append(lid_control)
            self.output(f"{label} Eye Lid Control").set(lid_control.ctl)

            aniseed_toolkit.shapes.scale(
                lid_control.ctl,
                scale_by=1,
                **{
                    forward_axis.lower(): 1,
                    up_axis.lower(): 0.0,
                    cross_axis.lower(): 0.5,
                }
            )

            aniseed_toolkit.shapes.offset(
                lid_control.ctl,
                offset_by=1,
                **{
                    forward_axis.lower(): 0.5,
                    up_axis.lower(): 0.2 * (1 if label == "Upper" else -1),
                    cross_axis.lower(): 0.0,
                }
            )

            aniseed_toolkit.constraints.parent_and_scale(
                lid_control.ctl,
                eye_lid_joint,
            )

        return lid_controls

    @classmethod
    def axis_vector(cls, axis):
        """
        Returns the unit vector for the given axis name (x, y or z). Anything
        other than x or y is treated as z.
        """

        if axis.lower() == "x":
            return [1, 0, 0]

        elif axis.lower() == "y":
            return [0, 1, 0]

        else:
            return [0, 0, 1]
