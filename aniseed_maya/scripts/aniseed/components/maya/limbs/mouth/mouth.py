import os
import typing

import aniseed
import aniseed_toolkit

import mref
from maya import cmds


class MouthComponent(aniseed.RigComponent):

    identifier = "Limb : Mouth"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
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
        self.user_func_create_skeleton()

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def input_widget(self, requirement_name: str):

        object_attributes = [
            "Parent",
            "Jaw Joint",
            "Upper Lip Joint",
            "Lower Lip Joint",
        ]

        for object_attribute in object_attributes:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

    def user_functions(self) -> typing.Dict[str, callable]:
        menu = super(MouthComponent, self).user_functions()

        if not self.input("Jaw Joint").get():
            menu["Create Joints"] = self.user_func_create_skeleton
            return menu

        return menu

    def run(self):

        # -- Start by getting our requirements
        parent = self.input("Parent").get()

        # -- Get our joints
        jaw_joint = self.input("Jaw Joint").get()
        upper_lip_joint = self.input("Upper Lip Joint").get()
        lower_lip_joint = self.input("Lower Lip Joint").get()

        # -- Get our options
        location = self.option("Location").get()

        jaw_length = aniseed_toolkit.run(
            "Distance Between",
            jaw_joint,
            lower_lip_joint,
        )

        # -- Create our component org to keep everything together
        component_org = aniseed_toolkit.run(
            "Create Basic Transform",
            classification=self.config.organisational,
            description="Mouth",
            location=location,
            config=self.config,
            parent=parent,
            match_to=jaw_joint
        )

        # -- Start by creating our jaw control
        jaw_control = aniseed_toolkit.control.create(
            description="Jaw",
            location=location,
            parent=component_org,
            shape="core_cube",
            config=self.config,
            match_to=jaw_joint,
        )
        self.output("Jaw Control").set(jaw_control.ctl)

        aniseed_toolkit.run(
            "Scale Shapes",
            jaw_control.ctl,
            scale_by=jaw_length,
            x=0.5,
            y=0,
            z=1,
        )

        aniseed_toolkit.run(
            "Offset Shapes",
            jaw_control.ctl,
            offset_by=jaw_length,
            x=0,
            y=0,
            z=0.5,
        )

        # -- Now add our animation attributes to the jaw control
        cmds.addAttr(
            jaw_control.ctl,
            shortName="StickyLips",
            attributeType="float",
            keyable=True,
            defaultValue=0,
            minValue=0,
            maxValue=1,
        )

        cmds.addAttr(
            jaw_control.ctl,
            shortName="LipBias",
            attributeType="float",
            keyable=True,
            defaultValue=0.5,
            minValue=0,
            maxValue=1,
        )
        sticky_lips_attr = f"{jaw_control.ctl}.StickyLips"
        sticky_bias_attr = f"{jaw_control.ctl}.LipBias"

        # -- The half jaw is constrained to both the parent and the
        # -- jaw
        half_jaw = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="rot",
            description="HalfJaw",
            location=location,
            config=self.config,
            parent=component_org,
            match_to=component_org
        )

        # -- Create our sticky lip nodes
        upper_lip_sticky = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="rot",
            description="UpperLipSticky",
            location=location,
            config=self.config,
            parent=component_org,
            match_to=component_org
        )

        lower_lip_sticky = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="rot",
            description="LowerLipSticky",
            location=location,
            config=self.config,
            parent=component_org,
            match_to=component_org
        )

        # --------------------------
        # -- Constraint the half jaw
        half_jaw_cns = cmds.parentConstraint(
            component_org,
            half_jaw,
        )[0]

        cmds.parentConstraint(
            jaw_control.ctl,
            half_jaw,
        )

        # -- Hook up our constraint driving connections
        half_jaw_reverse_node = cmds.createNode("reverse")

        cmds.connectAttr(
            sticky_bias_attr,
            half_jaw_cns + "." + cmds.parentConstraint(
                half_jaw_cns,
                query=True,
                weightAliasList=True,
            )[1]
        )

        cmds.connectAttr(
            sticky_bias_attr,
            f"{half_jaw_reverse_node}.inputX",
        )

        cmds.connectAttr(
            f"{half_jaw_reverse_node}.outputX",
            half_jaw_cns + "." + cmds.parentConstraint(
                half_jaw_cns,
                query=True,
                weightAliasList=True,
            )[0]
        )

        # --------------------------
        # -- Constrain the upper lip
        upper_lip_cns = cmds.parentConstraint(
            component_org,
            upper_lip_sticky,
        )[0]

        cmds.parentConstraint(
            half_jaw,
            upper_lip_sticky,
        )

        # -- Hook up our constraint driving connections
        upper_lip_reverse_node = cmds.createNode("reverse")

        cmds.connectAttr(
            sticky_lips_attr,
            upper_lip_cns + "." + cmds.parentConstraint(
                upper_lip_cns,
                query=True,
                weightAliasList=True,
            )[1]
        )

        cmds.connectAttr(
            sticky_lips_attr,
            f"{upper_lip_reverse_node}.inputX",
        )

        cmds.connectAttr(
            f"{upper_lip_reverse_node}.outputX",
            upper_lip_cns + "." + cmds.parentConstraint(
                upper_lip_cns,
                query=True,
                weightAliasList=True,
            )[0]
        )

        # --------------------------
        # -- Constrain the lower lip
        lower_lip_cns = cmds.parentConstraint(
            jaw_control.ctl,
            lower_lip_sticky,
        )[0]

        cmds.parentConstraint(
            half_jaw,
            lower_lip_sticky,
        )



        # -- Hook up our constraint driving connections
        lower_lip_reverse_node = cmds.createNode("reverse")

        cmds.connectAttr(
            sticky_lips_attr,
            lower_lip_cns + "." + cmds.parentConstraint(
                lower_lip_cns,
                query=True,
                weightAliasList=True,
            )[1]
        )

        cmds.connectAttr(
            sticky_lips_attr,
            f"{lower_lip_reverse_node}.inputX",
        )

        cmds.connectAttr(
            f"{lower_lip_reverse_node}.outputX",
            lower_lip_cns + "." + cmds.parentConstraint(
                lower_lip_cns,
                query=True,
                weightAliasList=True,
            )[0]
        )

        upper_lip_control = aniseed_toolkit.control.create(
            description="UpperLip",
            location=location,
            parent=upper_lip_sticky,
            shape="core_cube",
            rotate_shape=[0, 90, 0],
            config=self.config,
            match_to=upper_lip_joint,
        )
        self.output("Upper Lip Control").set(upper_lip_control.ctl)

        aniseed_toolkit.run(
            "Scale Shapes",
            upper_lip_control.ctl,
            scale_by=jaw_length * 0.2,
            x=1,
            y=0.5,
            z=0,
        )

        lower_lip_control = aniseed_toolkit.control.create(
            description="LowerLip",
            location=location,
            parent=lower_lip_sticky,
            shape="core_cube",
            rotate_shape=[0, 90, 0],
            config=self.config,
            match_to=lower_lip_joint,
        )
        self.output("Lower Lip Control").set(lower_lip_control.ctl)

        aniseed_toolkit.run(
            "Scale Shapes",
            lower_lip_control.ctl,
            scale_by=jaw_length * 0.2,
            x=1,
            y=0.5,
            z=0,
        )

        # -- If we need to create the aim control, set that up now
        if self.option("Use Aim Control").get():

            chain_direction = aniseed_toolkit.run(
                "Get Chain Facing Direction",
                jaw_joint,
                lower_lip_joint,
                epsilon=aniseed_toolkit.run(
                    "Distance Between",
                    jaw_joint,
                    lower_lip_joint,
                ) * 0.3,
            )

            aim_control = aniseed_toolkit.control.create(
                description="JawAim",
                location=location,
                parent=component_org,
                shape="core_sphere",
                rotate_shape=[0, 90, 0],
                config=self.config,
                match_to=jaw_joint,
            )

            aniseed_toolkit.run(
                "Scale Shapes",
                aim_control.ctl,
                scale_by=jaw_length,
                x=0.25,
                y=0.25,
                z=0,
            )

            aniseed_toolkit.guide.link(
                aim_control.ctl,
                jaw_control.ctl,
            )

            cmds.setAttr(
                f"{aim_control.org}.translate{chain_direction.axis.upper()}",
                jaw_length * self.option("Aim Control Distance Multiplier").get(),
            )

            aim_node = aniseed_toolkit.run(
                "Create Basic Transform",
                classification="aim",
                description="JawAimSolver",
                location=location,
                config=self.config,
                parent=component_org,
                match_to=component_org
            )

            aim_upvector = aniseed_toolkit.run(
                "Create Basic Transform",
                classification="aim",
                description="JawAimUpvector",
                location=location,
                config=self.config,
                parent=component_org,
                match_to=component_org
            )

            cmds.setAttr(
                f"{aim_upvector}.translate{chain_direction.cross_axis.upper()}",
                10,
            )

            cmds.aimConstraint(
                aim_control.ctl,
                aim_node,
                aimVector=chain_direction.axis_vector,
                upVector=aniseed_toolkit.run("Get Direction Class", chain_direction.cross_axis).axis_vector,
                worldUpType="object",
                worldUpObject=aim_upvector,
                maintainOffset=False,
            )

            # -- Now constrain the zro of the jaw control
            cmds.parentConstraint(
                aim_node,
                jaw_control.zero,
                maintainOffset=True,
            )

            # -- Add proxy attributes to the control
            cmds.addAttr(
                aim_control.ctl,
                shortName="StickyLips",
                proxy=f"{jaw_control.ctl}.StickyLips",
                keyable=True,
                defaultValue=0,
                minValue=0,
                maxValue=1,
            )

            cmds.addAttr(
                aim_control.ctl,
                shortName="LipBias",
                proxy=f"{jaw_control.ctl}.LipBias",
                keyable=True,
                defaultValue=0.5,
                minValue=0,
                maxValue=1,
            )

        # -- Now we create the actual controls for the lps
        # -- Finally we now create the constraints for the joints
        for constraint_type in [cmds.parentConstraint, cmds.scaleConstraint]:
            constraint_type(
                upper_lip_control.ctl,
                upper_lip_joint,
                maintainOffset=True,
            )

            constraint_type(
                lower_lip_control.ctl,
                lower_lip_joint,
                maintainOffset=True,
            )

            constraint_type(
                jaw_control.ctl,
                jaw_joint,
                maintainOffset=True,
            )

    def user_func_create_skeleton(self):

        parent = aniseed_toolkit.mutils.first_selected()

        # -- Create the jaw and the lower lip
        jaw_joint = aniseed_toolkit.joints.create(
            description="Jaw",
            location=self.option("Location").get(),
            parent=parent,
            config=self.config,
        )

        lower_lip_joint = aniseed_toolkit.joints.create(
            description="LowerLip",
            location=self.option("Location").get(),
            parent=jaw_joint,
            match_to=jaw_joint,
            config=self.config,
        )
        cmds.setAttr(f"{lower_lip_joint}.tz", aniseed_toolkit.units.from_cm(4))

        # -- If we have a parent, then snap the jaw to the parent position
        if parent:
            aniseed_toolkit.transformation.snap_position(jaw_joint, parent)

        # -- Now we create the upper lip
        upper_lip_joint = aniseed_toolkit.joints.create(
            description="UpperLip",
            location=self.option("Location").get(),
            match_to=lower_lip_joint,
            parent=parent,
            config=self.config,
        )

        self.input("Jaw Joint").set(jaw_joint)
        self.input("Upper Lip Joint").set(upper_lip_joint)
        self.input("Lower Lip Joint").set(lower_lip_joint)
