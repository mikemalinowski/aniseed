"""
Provides the "Limb : Mouth" component, which rigs a jaw joint and upper and
lower lip joints. The jaw control carries StickyLips and LipBias attributes that
blend the lip controls between the parent and the jaw, and an optional aim
control can drive the jaw. Joints can be created for the user on entering the
stack.
"""
import os
import mref
import typing
import aniseed
import aniseed_toolkit


class MouthComponent(aniseed.RigComponent):

    identifier = "Limb : Mouth"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, jaw and upper/lower lip joint inputs, the naming
        and aim control options and the jaw and lip control outputs.
        """
        super(MouthComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            group="Control Rig",
        )

        self.declare_input(
            name="Jaw Joint",
            group="Joint Requirements",
        )

        self.declare_input(
            name="Upper Lip Joint",
            group="Joint Requirements",
        )

        self.declare_input(
            name="Lower Lip Joint",
            group="Joint Requirements",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Naming Prefix",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Use Aim Control",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Aim Control Distance Multiplier",
            value=1.0,
            group="Behaviour",
        )

        self.declare_output(
            "Jaw Control",
        )

        self.declare_output(
            "Upper Lip Control",
        )

        self.declare_output(
            "Lower Lip Control",
        )

    def on_enter_stack(self):
        """
        Creates the mouth joints (relative to the current selection) and hooks
        the Parent input to the parent component's default output.
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

    def option_widget(self, option_name: str):
        """
        Returns a location selector for the Location option.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Adds a "Create Joints" menu entry when no jaw joint has been set.
        """
        menu = super(MouthComponent, self).user_functions()

        if not self.input("Jaw Joint").get():
            menu["Create Joints"] = self.user_func_create_skeleton

        return menu

    def run(self):
        """
        Builds the jaw and upper/lower lip controls. StickyLips and LipBias
        attributes on the jaw control blend the lips between the parent, the
        jaw and a half-jaw transform. If Use Aim Control is set, the jaw is
        additionally driven by an aim control (which proxies those attributes).
        The joints are parent and scale constrained to their controls.
        """

        # -- Get our joints
        jaw_joint = self.input("Jaw Joint").get()
        upper_lip_joint = self.input("Upper Lip Joint").get()
        lower_lip_joint = self.input("Lower Lip Joint").get()

        # -- Get our options
        location = self.option("Location").get()
        prefix = self.option("Naming Prefix").get()

        if prefix:
            prefix += "_"

        jaw_length = aniseed_toolkit.core.maths.distance_between(
            jaw_joint,
            lower_lip_joint,
        )

        # -- Create our component org to keep everything together
        component_org = aniseed_toolkit.scene.transforms.create(
            classification=self.config.organisational,
            description=prefix + "Mouth",
            location=location,
            config=self.config,
            parent=self.input("Parent").get(),
            match_to=jaw_joint
        )

        # -- Start by creating our jaw control
        jaw_control = aniseed_toolkit.rig.control.create(
            description=prefix + "Jaw",
            location=location,
            parent=component_org,
            shape="core_cube",
            config=self.config,
            match_to=jaw_joint,
        )
        self.output("Jaw Control").set(jaw_control.ctl)

        aniseed_toolkit.scene.shapes.scale(
            jaw_control.ctl,
            scale_by=jaw_length,
            x=0.5,
            y=0,
            z=1,
        )

        aniseed_toolkit.scene.shapes.offset(
            jaw_control.ctl,
            offset_by=jaw_length,
            x=0,
            y=0,
            z=0.5,
        )

        # -- Now add our animation attributes to the jaw control
        jaw_controller = mref.get(jaw_control.ctl)
        sticky_lips_attr = jaw_controller.add_attribute(
            "StickyLips",
            value=None,
            attribute_type="float",
            keyable=True,
            defaultValue=0,
            minValue=0,
            maxValue=1,
        )

        sticky_bias_attr = jaw_controller.add_attribute(
            "LipBias",
            value=None,
            attribute_type="float",
            keyable=True,
            defaultValue=0.5,
            minValue=0,
            maxValue=1,
        )

        # -- The half jaw is constrained to both the parent and the
        # -- jaw
        half_jaw = self._create_mechanism_transform("HalfJaw", prefix, location, component_org)

        # -- Create our sticky lip nodes
        upper_lip_sticky = self._create_mechanism_transform("UpperLipSticky", prefix, location, component_org)
        lower_lip_sticky = self._create_mechanism_transform("LowerLipSticky", prefix, location, component_org)

        # -- Constrain the half jaw, upper lip and lower lip between
        # -- their two drivers
        self._constrain_between(sticky_bias_attr, component_org, jaw_control.ctl, half_jaw)
        self._constrain_between(sticky_lips_attr, component_org, half_jaw, upper_lip_sticky)
        self._constrain_between(sticky_lips_attr, jaw_control.ctl, half_jaw, lower_lip_sticky)

        upper_lip_control = self._create_lip_control("UpperLip", prefix, location, upper_lip_sticky, upper_lip_joint, jaw_length)
        self.output("Upper Lip Control").set(upper_lip_control.ctl)

        lower_lip_control = self._create_lip_control("LowerLip", prefix, location, lower_lip_sticky, lower_lip_joint, jaw_length)
        self.output("Lower Lip Control").set(lower_lip_control.ctl)

        # -- If we need to create the aim control, set that up now
        if self.option("Use Aim Control").get():

            chain_direction = aniseed_toolkit.scene.joints.get_chain_facing_direction(
                jaw_joint,
                lower_lip_joint,
                epsilon=jaw_length * 0.3,
            )

            aim_control = aniseed_toolkit.rig.control.create(
                description=prefix + "JawAim",
                location=location,
                parent=component_org,
                shape="core_sphere",
                rotate_shape=[0, 90, 0],
                config=self.config,
                match_to=jaw_joint,
            )

            aniseed_toolkit.scene.shapes.scale(
                aim_control.ctl,
                scale_by=jaw_length,
                x=0.25,
                y=0.25,
                z=0,
            )

            aniseed_toolkit.rig.guide.link(
                aim_control.ctl,
                jaw_control.ctl,
            )

            mref.get(aim_control.org).attr(f"translate{chain_direction.axis.upper()}").set(
                jaw_length * self.option("Aim Control Distance Multiplier").get(),
            )

            aim_node = aniseed_toolkit.scene.transforms.create(
                classification="aim",
                description=prefix + "JawAimSolver",
                location=location,
                config=self.config,
                parent=component_org,
                match_to=component_org
            )

            aim_upvector = mref.get(
                aniseed_toolkit.scene.transforms.create(
                    classification="aim",
                    description=prefix + "JawAimUpvector",
                    location=location,
                    config=self.config,
                    parent=component_org,
                    match_to=component_org
                ),
            )
            aim_upvector.attr(f"translate{chain_direction.cross_axis.upper()}").set(10)

            mref.aimConstraint(
                aim_control.ctl,
                aim_node,
                aimVector=chain_direction.axis_vector,
                upVector=aniseed_toolkit.core.direction.Direction(chain_direction.cross_axis).axis_vector,
                worldUpType="object",
                worldUpObject=aim_upvector,
                maintainOffset=False,
            )

            # -- Now constrain the zro of the jaw control
            mref.parentConstraint(
                aim_node,
                jaw_control.zero,
                maintainOffset=True,
            )

            # -- Add proxy attributes to the control
            aim_controller = mref.get(aim_control.ctl)
            aim_controller.add_proxy(
                "StickyLips",
                sticky_lips_attr,
                defaultValue=0,
                minValue=0,
                maxValue=1,
            )

            aim_controller.add_proxy(
                "LipBias",
                sticky_bias_attr,
                defaultValue=0.5,
                minValue=0,
                maxValue=1,
            )

        # -- Finally we now create the constraints for the joints
        for constraint_type in [mref.parentConstraint, mref.scaleConstraint]:
            for control, joint in [
                (upper_lip_control, upper_lip_joint),
                (lower_lip_control, lower_lip_joint),
                (jaw_control, jaw_joint),
            ]:
                constraint_type(
                    control.ctl,
                    joint,
                    maintainOffset=True,
                )

    def _create_mechanism_transform(self, description, prefix, location, component_org) -> str:
        """
        Creates a mechanical transform under (and matched to) the component org
        """
        return aniseed_toolkit.scene.transforms.create(
            classification="rot",
            description=prefix + description,
            location=location,
            config=self.config,
            parent=component_org,
            match_to=component_org
        )

    @classmethod
    def _constrain_between(cls, attribute, first_driver, second_driver, driven):
        """
        Parent constrains the driven node to both drivers, with the given
        attribute blending between them (0 being the first driver and 1
        being the second).
        """
        constraint = mref.parentConstraint(first_driver, driven)[0]
        mref.parentConstraint(second_driver, driven)

        aniseed_toolkit.scene.constraints.blend_weights(attribute, constraint)

    def _create_lip_control(self, description, prefix, location, parent, match_to, jaw_length):
        """
        Creates a lip control, scaling its shape relative to the jaw length
        """
        lip_control = aniseed_toolkit.rig.control.create(
            description=prefix + description,
            location=location,
            parent=parent,
            shape="core_cube",
            rotate_shape=[0, 90, 0],
            config=self.config,
            match_to=match_to,
        )

        aniseed_toolkit.scene.shapes.scale(
            lip_control.ctl,
            scale_by=jaw_length * 0.2,
            x=1,
            y=0.5,
            z=0,
        )
        return lip_control

    def user_func_create_skeleton(self):
        """
        Creates a jaw joint with a child lower lip joint (4cm along Z) and an
        upper lip joint at the lower lip position, then sets the joint inputs.
        The joints are parented to, and the jaw snapped to, the first selected
        object if there is one.
        """

        parent = aniseed_toolkit.core.selection.first_selected()
        location = self.option("Location").get()
        prefix = self.option("Naming Prefix").get()

        if prefix:
            prefix += "_"

        # -- Create the jaw and the lower lip
        jaw_joint = aniseed_toolkit.scene.joints.create(
            description=prefix + "Jaw",
            location=location,
            parent=parent,
            config=self.config,
        )

        lower_lip_joint = aniseed_toolkit.scene.joints.create(
            description=prefix + "LowerLip",
            location=location,
            parent=jaw_joint,
            match_to=jaw_joint,
            config=self.config,
        )
        mref.get(lower_lip_joint).translateZ.set(aniseed_toolkit.core.units.from_cm(4))

        # -- If we have a parent, then snap the jaw to the parent position
        if parent:
            aniseed_toolkit.scene.transforms.snap_position(jaw_joint, parent)

        # -- Now we create the upper lip
        upper_lip_joint = aniseed_toolkit.scene.joints.create(
            description=prefix + "UpperLip",
            location=location,
            match_to=lower_lip_joint,
            parent=parent,
            config=self.config,
        )

        self.input("Jaw Joint").set(jaw_joint)
        self.input("Upper Lip Joint").set(upper_lip_joint)
        self.input("Lower Lip Joint").set(lower_lip_joint)
