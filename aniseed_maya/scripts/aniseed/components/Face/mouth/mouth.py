import bony
import typing
import shapeshift

import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
class MouthComponent(aniseed.RigComponent):

    identifier = "Face : Mouth"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(MouthComponent, self).__init__(*args, **kwargs)

        self.declare_requirement(
            name="Parent",
            group="Control Rig",
        )

        self.declare_requirement(
            name="Jaw Joint",
            group="Joint Requirements",
        )

        self.declare_requirement(
            name="Upper Lip Joint",
            group="Joint Requirements",
        )

        self.declare_requirement(
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

        self.declare_output(
            "Jaw Control",
        )

        self.declare_output(
            "Upper Lip Control",
        )

        self.declare_output(
            "Lower Lip Control",
        )

    # ----------------------------------------------------------------------------------
    def requirement_widget(self, requirement_name: str) -> "PySide6.QWidget":

        object_attributes = [
            "Parent",
            "Jaw Joint",
            "Upper Lip Joint",
            "Lower Lip Joint",
        ]

        for object_attribute in object_attributes:
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def option_widget(self, option_name: str) -> "PySide6.QWidget":
        if option_name == "Location":
            return aniseed.widgets.everywhere.LocationSelector(config=self.config)

    # ----------------------------------------------------------------------------------
    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Joints": self.create_joints,
        }

    # ----------------------------------------------------------------------------------
    def run(self) -> bool:

        # -- Start by getting our requirements
        parent = self.requirement("Parent").get()

        # -- Get our joints
        jaw_joint = self.requirement("Jaw Joint").get()
        upper_lip_joint = self.requirement("Upper Lip Joint").get()
        lower_lip_joint = self.requirement("Lower Lip Joint").get()

        # -- Get our options
        location = self.option("Location").get()

        jaw_length = bony.math.distance_between(
            jaw_joint,
            lower_lip_joint,
        )

        # -- Create our component org to keep everything together
        component_org = aniseed.control.basic_transform(
            classification=self.config.organisational,
            description="Mouth",
            location=location,
            config=self.config,
            parent=parent,
            match_to=jaw_joint
        )

        # -- Start by creating our jaw control
        jaw_control = aniseed.control.create(
            description="Jaw",
            location=location,
            parent=component_org,
            shape="core_cube",
            config=self.config,
            match_to=jaw_joint,
        )
        self.output("Jaw Control").set(jaw_control)


        shapeshift.scale(
            jaw_control,
            scale_by=jaw_length,
            x=1,
            y=0,
            z=0.5,
        )

        shapeshift.offset(
            jaw_control,
            offset_by=jaw_length,
            x=0.5,
            y=0,
            z=0,
        )

        # -- Now add our animation attributes to the jaw control
        mc.addAttr(
            jaw_control,
            shortName="StickyLips",
            at="float",
            k=True,
            dv=0,
            min=0,
            max=1,
        )

        mc.addAttr(
            jaw_control,
            shortName="LipBias",
            at="float",
            k=True,
            dv=0.5,
            min=0,
            max=1,
        )
        sticky_lips_attr = f"{jaw_control}.StickyLips"
        sticky_bias_attr = f"{jaw_control}.LipBias"

        jaw_zro = aniseed.control.get_classification(
            jaw_control,
            "zro",
        )

        # -- The half jaw is constrained to both the parent and the
        # -- jaw
        half_jaw = aniseed.control.basic_transform(
            classification="rot",
            description="HalfJaw",
            location=location,
            config=self.config,
            parent=component_org,
            match_to=component_org
        )

        # -- Create our sticky lip nodes
        upper_lip_sticky = aniseed.control.basic_transform(
            classification="rot",
            description="UpperLipSticky",
            location=location,
            config=self.config,
            parent=component_org,
            match_to=component_org
        )

        lower_lip_sticky = aniseed.control.basic_transform(
            classification="rot",
            description="LowerLipSticky",
            location=location,
            config=self.config,
            parent=component_org,
            match_to=component_org
        )

        # --------------------------
        # -- Constraint the half jaw
        half_jaw_cns = mc.parentConstraint(
            component_org,
            half_jaw,
        )[0]

        mc.parentConstraint(
            jaw_control,
            half_jaw,
        )

        # -- Hook up our constraint driving connections
        half_jaw_reverse_node = mc.createNode("reverse")

        mc.connectAttr(
            sticky_bias_attr,
            half_jaw_cns + "." + mc.parentConstraint(
                half_jaw_cns,
                query=True,
                weightAliasList=True,
            )[1]
        )

        mc.connectAttr(
            sticky_bias_attr,
            f"{half_jaw_reverse_node}.inputX",
        )

        mc.connectAttr(
            f"{half_jaw_reverse_node}.outputX",
            half_jaw_cns + "." + mc.parentConstraint(
                half_jaw_cns,
                query=True,
                weightAliasList=True,
            )[0]
        )

        # --------------------------
        # -- Constrain the upper lip
        upper_lip_cns = mc.parentConstraint(
            component_org,
            upper_lip_sticky,
        )[0]

        mc.parentConstraint(
            half_jaw,
            upper_lip_sticky,
        )

        # -- Hook up our constraint driving connections
        upper_lip_reverse_node = mc.createNode("reverse")

        mc.connectAttr(
            sticky_lips_attr,
            upper_lip_cns + "." + mc.parentConstraint(
                upper_lip_cns,
                query=True,
                weightAliasList=True,
            )[1]
        )

        mc.connectAttr(
            sticky_lips_attr,
            f"{upper_lip_reverse_node}.inputX",
        )

        mc.connectAttr(
            f"{upper_lip_reverse_node}.outputX",
            upper_lip_cns + "." + mc.parentConstraint(
                upper_lip_cns,
                query=True,
                weightAliasList=True,
            )[0]
        )

        # --------------------------
        # -- Constrain the lower lip
        lower_lip_cns = mc.parentConstraint(
            jaw_control,
            lower_lip_sticky,
        )[0]

        mc.parentConstraint(
            half_jaw,
            lower_lip_sticky,
        )


        # -- Hook up our constraint driving connections
        lower_lip_reverse_node = mc.createNode("reverse")

        mc.connectAttr(
            sticky_lips_attr,
            lower_lip_cns + "." + mc.parentConstraint(
                lower_lip_cns,
                query=True,
                weightAliasList=True,
            )[1]
        )

        mc.connectAttr(
            sticky_lips_attr,
            f"{lower_lip_reverse_node}.inputX",
        )

        mc.connectAttr(
            f"{lower_lip_reverse_node}.outputX",
            lower_lip_cns + "." + mc.parentConstraint(
                lower_lip_cns,
                query=True,
                weightAliasList=True,
            )[0]
        )

        upper_lip_control = aniseed.control.create(
            description="UpperLip",
            location=location,
            parent=upper_lip_sticky,
            shape="core_cube",
            config=self.config,
            match_to=upper_lip_joint,
        )
        self.output("Upper Lip Control").set(upper_lip_control)

        shapeshift.scale(
            upper_lip_control,
            scale_by=jaw_length * 0.2,
            x=0,
            y=0.5,
            z=1,
        )

        lower_lip_control = aniseed.control.create(
            description="LowerLip",
            location=location,
            parent=lower_lip_sticky,
            shape="core_cube",
            config=self.config,
            match_to=lower_lip_joint,
        )
        self.output("Lower Lip Control").set(lower_lip_control)

        shapeshift.scale(
            lower_lip_control,
            scale_by=jaw_length * 0.2,
            x=0,
            y=0.5,
            z=1,
        )

        # -- If we need to create the aim control, set that up now
        if self.option("Use Aim Control").get():

            facing_axis = bony.direction.get_axis_from_direction(
                bony.direction.get_chain_facing_direction(
                    jaw_joint,
                    lower_lip_joint,
                    epsilon=bony.math.distance_between(
                        jaw_joint,
                        lower_lip_joint,
                    ) * 0.5,
                ),
            )


            aim_control = aniseed.control.create(
                description="JawAim",
                location=location,
                parent=component_org,
                shape="core_sphere",
                config=self.config,
                match_to=jaw_joint,
            )

            shapeshift.scale(
                aim_control,
                scale_by=jaw_length,
                x=0,
                y=0.25,
                z=0.25,
            )

            aim_org = aniseed.control.get_classification(
                aim_control,
                "org",
            )

            mc.setAttr(
                f"{aim_org}.translate{facing_axis}",
                jaw_length * 1.2,
            )

            aim_node = aniseed.control.basic_transform(
                classification="aim",
                description="JawAimSolver",
                location=location,
                config=self.config,
                parent=component_org,
                match_to=component_org
            )

            aim_upvector = aniseed.control.basic_transform(
                classification="aim",
                description="JawAimUpvector",
                location=location,
                config=self.config,
                parent=component_org,
                match_to=component_org
            )

            upvector_axis = bony.direction.get_cross_axis(facing_axis)

            mc.setAttr(
                f"{aim_upvector}.translate{upvector_axis}",
                10,
            )

            mc.aimConstraint(
                aim_control,
                aim_node,
                aimVector=bony.direction.axis_vector(facing_axis),
                upVector=bony.direction.axis_vector(upvector_axis),
                worldUpType="object",
                worldUpObject=aim_upvector,
                maintainOffset=False,
            )

            # -- Now constrain the zro of the jaw control
            mc.parentConstraint(
                aim_node,
                aniseed.control.get_classification(
                    jaw_control,
                    "zro",
                ),
                maintainOffset=True,
            )

            # -- Add proxy attributes to the control
            mc.addAttr(
                aim_control,
                shortName="StickyLips",
                proxy=f"{jaw_control}.StickyLips",
                k=True,
                dv=0,
                min=0,
                max=1,
            )

            mc.addAttr(
                aim_control,
                shortName="LipBias",
                proxy=f"{jaw_control}.LipBias",
                k=True,
                dv=0.5,
                min=0,
                max=1,
            )

        # -- Now we create the actual controls for the lps
        # -- Finally we now create the constraints for the joints
        mc.parentConstraint(
            upper_lip_control,
            upper_lip_joint,
            maintainOffset=True,
        )

        mc.parentConstraint(
            lower_lip_control,
            lower_lip_joint,
            maintainOffset=True,
        )

        mc.parentConstraint(
            jaw_control,
            jaw_joint,
            maintainOffset=True,
        )

    # ----------------------------------------------------------------------------------
    def create_joints(self):

        parent = mc.ls(sl=True)[0]

        jaw_joint = mc.rename(
            mc.joint(),
            self.config.generate_name(
                classification=self.config.joint,
                description="Jaw",
                location=self.option("Location").get(),
            ),
        )
        mc.setAttr(f"{jaw_joint}.tx", -1.3)
        mc.setAttr(f"{jaw_joint}.ty", -1.4)
        mc.setAttr(f"{jaw_joint}.rz", -120)

        lower_lip_joint = mc.rename(
            mc.joint(),
            self.config.generate_name(
                classification=self.config.joint,
                description="LowerLip",
                location=self.option("Location").get(),
            ),
        )
        mc.setAttr(f"{lower_lip_joint}.tx", 3.685)

        mc.select(parent)

        upper_lip_joint = mc.rename(
            mc.joint(),
            self.config.generate_name(
                classification=self.config.joint,
                description="UpperLip",
                location=self.option("Location").get(),
            ),
        )
        mc.setAttr(f"{upper_lip_joint}.tx", -2.780)
        mc.setAttr(f"{upper_lip_joint}.ty", -4.800)
        mc.setAttr(f"{upper_lip_joint}.rz", -120)

        self.requirement("Jaw Joint").set(jaw_joint)
        self.requirement("Upper Lip Joint").set(upper_lip_joint)
        self.requirement("Lower Lip Joint").set(lower_lip_joint)
