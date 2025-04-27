import os
import typing
import aniseed
import aniseed_toolkit

import maya.cmds as mc


class EyesComponent(aniseed.RigComponent):
    """
    This component adds a left and right eye
    """

    identifier = "Face : Eyes"

    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
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
            name="Aim Distance",
            value=30,
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

    def input_widget(self, requirement_name: str):

        object_attributes = [
            "Parent",
            "Jaw Joint",
            "Upper Lip Joint",
            "Lower Lip Joint",
        ]

        for object_attribute in object_attributes:
            return aniseed.widgets.ObjectSelector(component=self)

    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Joints": self.create_joints,
        }

    def run(self):

        components = self._get_components()

        lf_eye_component = components[0]
        rt_eye_component = components[1]

        lf_eye_component.run()
        rt_eye_component.run()

        left_aim_control = aniseed_toolkit.run(
            "Get Control",
            lf_eye_component.output("Aim Control").get(),
        )
        right_aim_control = aniseed_toolkit.run(
            "Get Control",
            lf_eye_component.output("Aim Control").get(),
        )

        # -- Create the control to act as the master aim
        master_aim_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.option('Name').get()}AimMaster",
            location=self.config.middle,
            config=self.config,
            shape="core_sphere",
            parent=self.input("Parent").get(),
            match_to=lf_eye_component.output("Aim Control").get(),
        )

        ws_left = mc.xform(
            left_aim_control.ctl,
            translation=True,
            query=True,
            worldSpace=True,
        )

        ws_right = mc.xform(
            right_aim_control.ctl,
            translation=True,
            query=True,
            worldSpace=True,
        )

        mc.xform(
            master_aim_control.org,
            translation=[
                (ws_left[0] + ws_right[0]) * 0.5,
                (ws_left[1] + ws_right[1]) * 0.5,
                (ws_left[2] + ws_right[2]) * 0.5,
            ],
            worldSpace=True,
        )

        mc.parent(
            left_aim_control.org,
            master_aim_control.ctl,
        )

        mc.parent(
            right_aim_control.org,
            master_aim_control.ctl,
        )

        # -- Set all our outputs
        self.output("Left Eye Control").set(lf_eye_component.output("Eye Control").get())
        self.output("Left Aim Control").set(lf_eye_component.output("Aim Control").get())
        self.output("Right Eye Control").set(rt_eye_component.output("Eye Control").get())
        self.output("Right Aim Control").set(rt_eye_component.output("Aim Control").get())
        self.output("Central Aim Control").set(master_aim_control.ctl)

    def _get_components(self):

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

        # -- Now set the side specific requirements
        lf_eye_component.input("Eye Joint").set(
            self.input("Left Eye Joint").get(),
        )

        rt_eye_component.input("Eye Joint").set(
            self.input("Right Eye Joint").get(),
        )

        lf_eye_component.input("Lower Eye Lid Joint").set(
            self.input("Left Lower Eye Lid Joint").get(),
        )

        rt_eye_component.input("Lower Eye Lid Joint").set(
            self.input("Right Lower Eye Lid Joint").get(),
        )

        lf_eye_component.input("Upper Eye Lid Joint").set(
            self.input("Left Upper Eye Lid Joint").get(),
        )

        rt_eye_component.input("Upper Eye Lid Joint").set(
            self.input("Right Upper Eye Lid Joint").get(),
        )

        lf_eye_component.option("Location").set(
            self.config.left,
        )

        rt_eye_component.option("Location").set(
            self.config.right,
        )

        return components

    def create_joints(self):

        parent = mc.ls(sl=True)[0]
        multipliers = [1, -1]

        # -- Work out the horizontal axis
        all_axis = ["X", "Y", "Z"]

        all_axis.remove(self.option("Forward Axis").get())
        all_axis.remove(self.option("Up Axis").get())

        cross_axis = all_axis[0]

        labels = ["Left", "Right"]
        components = self._get_components()

        for idx, component in enumerate(components):

            label = labels[idx]
            mc.select(parent)

            root_joint = component.create_joints()

            mc.setAttr(
                f"{root_joint}.translate{cross_axis.upper()}",
                (self.option("Aim Distance").get() * 0.2) * multipliers[idx],
            )

            # -- Now set the side specific requirements
            self.input(f"{label} Eye Joint").set(
                component.input("Eye Joint").get(),
            )

            self.input(f"{label} Eye Joint").set(
                component.input("Eye Joint").get(),
            )

            self.input(f"{label} Lower Eye Lid Joint").set(
                component.input("Lower Eye Lid Joint").get(),
            )

            self.input(f"{label} Lower Eye Lid Joint").set(
                component.input("Lower Eye Lid Joint").get(),
            )

            self.input(f"{label} Upper Eye Lid Joint").set(
                component.input("Upper Eye Lid Joint").get(),
            )

            self.input(f"{label} Upper Eye Lid Joint").set(
                component.input("Upper Eye Lid Joint").get(),
            )


class EyeComponent(aniseed.RigComponent):
    """
    This is a single eye component
    """
    identifier = "Standard : Eye"

    def __init__(self, *args, **kwargs):
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
            value=30,
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

        self.declare_output(
            name="Eye Control",
        )

        self.declare_output(
            name="Aim Control",
        )

    def input_widget(self, requirement_name: str):

        object_requirements = [
            "Parent",
            "Eye Joint",
            "Upper Eyelid Joint",
            "Lower Eyelid Joint",
        ]

        if requirement_name in object_requirements:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name in ["Forward Axis", "Up Axis"]:
            return aniseed.widgets.AxisSelector()

    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Joints": self.create_joints,
        }

    def create_joints(self):

        try:
            parent = mc.ls(sl=True)[0]

        except IndexError:
            return

        if not mc.nodeType(parent) == "joint":
            print("You should create the eye joints within the joint hierarchy")
            return

        mc.select(clear=True)

        eye_joint = mc.rename(
            mc.joint(),
            self.config.generate_name(
                classification=self.config.joint,
                description=self.option("Name").get(),
                location=self.option("Location").get(),
            ),
        )

        self.input("Eye Joint").set(eye_joint)

        for label in ["Lower", "Upper"]:
            mc.select(eye_joint)

            lid_joint = mc.rename(
                mc.joint(),
                self.config.generate_name(
                    classification=self.config.joint,
                    description=self.option("Name").get() + f"{label}Lid",
                    location=self.option("Location").get(),
                ),
            )

            self.input(f"{label} Eye Lid Joint").set(lid_joint)

        mc.parent(
            eye_joint,
            parent,
        )

        mc.xform(
            eye_joint,
            matrix=mc.xform(
                parent,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        mc.xform(
            eye_joint,
            rotation=[0, -90, 0],
            worldSpace=True,
        )

        return eye_joint

    def run(self):

        parent = self.input("Parent").get()
        eye_joint = self.input("Eye Joint").get()

        description = self.option("Name").get()
        location = self.option("Location").get()

        aim_distance = self.option("Aim Distance").get()
        forward_axis = self.option("Forward Axis").get()
        up_axis = self.option("Up Axis").get()

        align_to_world = self.option("Align Controls To World").get()

        # -- Create a node to place everything under
        component_org = mc.rename(
            mc.createNode("transform"),
            self.config.generate_name(
                classification=self.config.organisational,
                description=description + "Component",
                location=location,
            ),
        )

        mc.parent(
            component_org,
            parent,
        )

        # -- Create our eye control
        direct_eye_control = aniseed_toolkit.run(
            "Create Control",
            description=description,
            location=location,
            parent=component_org,
            match_to=eye_joint,
            config=self.config,
            shape="core_sphere",
        )

        # -- Create our aim control and move it to the right place
        aim_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{description}Aim",
            location=location,
            parent=direct_eye_control.ctl,
            match_to=eye_joint,
            shape="core_sphere",
            config=self.config,
        )

        self.output("Eye Control").set(direct_eye_control.ctl)
        self.output("Aim Control").set(aim_control.ctl)

        mc.setAttr(
            f"{aim_control.org}.translate{forward_axis}",
            aim_distance,
        )

        # -- Parent the aim to be a child of the component org
        mc.parent(
            aim_control.org,
            component_org,
        )

        # -- Align the controls if we need to
        if align_to_world:

            mc.xform(
                direct_eye_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

            mc.xform(
                aim_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Create the upvector
        upvector = mc.rename(
            mc.createNode("transform"),
            self.config.generate_name(
                classification="upv",
                description=description + "AimStabilizer",
                location=location,
            ),
        )

        mc.xform(
            upvector,
            matrix=mc.xform(direct_eye_control.ctl, q=True, ws=True, m=True),
            worldSpace=True,
        )

        mc.parent(
            upvector,
            direct_eye_control.ctl,
        )

        mc.setAttr(
            f"{upvector}.translate{up_axis}",
            10,
        )

        mc.parent(
            upvector,
            component_org,
        )

        # -- Create the aim setup
        aim_node = mc.rename(
            mc.createNode("transform"),
            self.config.generate_name(
                classification="aim",
                description=description,
                location=location,
            ),
        )

        mc.parent(
            aim_node,
            component_org,
        )

        mc.xform(
            aim_node,
            matrix=mc.xform(direct_eye_control.ctl, q=True, ws=True, m=True),
            worldSpace=True,
        )

        aim_cns = mc.aimConstraint(
            aim_control.ctl,
            aim_node,
            worldUpType="object",
            worldUpObject=upvector,
            aimVector=self.axis_vector(forward_axis),
            upVector=self.axis_vector(up_axis),
            maintainOffset=False,
        )

        # -- Constrain the joint
        mc.parentConstraint(
            aim_node,
            direct_eye_control.org,
            maintainOffset=True,
        )

        mc.parentConstraint(
            direct_eye_control.ctl,
            eye_joint,
            maintainOffset=True,
        )

        self.create_eyelid_behaviour(
            component_org=component_org,
            eye_control=direct_eye_control.ctl,
            aim_control=aim_control.ctl,
        )

    def create_eyelid_behaviour(self, component_org, eye_control, aim_control):

        parent = self.input("Parent").get()
        eye_joint = self.input("Eye Joint").get()

        description = self.option("Name").get()
        location = self.option("Location").get()

        aim_distance = self.option("Aim Distance").get()
        forward_axis = self.option("Forward Axis").get()
        up_axis = self.option("Up Axis").get()

        # -- Work out the horizontal axis
        all_axis = ["X", "Y", "Z"]

        all_axis.remove(forward_axis)
        all_axis.remove(up_axis)
        cross_axis = all_axis[0]


        aniseed_toolkit.run("Add Separator Attribute", eye_control)
        aniseed_toolkit.run("Add Separator Attribute", aim_control)

        # -- Add the attribute we will use to blend the behaviour out
        mc.addAttr(
            eye_control,
            shortName="autoEyelids",
            at="float",
            dv=1,
            k=True,
        )
        aniseed_toolkit.run("Add Separator Attribute", eye_control)

        mc.addAttr(
            eye_control,
            shortName="upperLidFollow",
            at="float",
            dv=self.option("Default Upper Lid Follow").get(),
            k=True,
        )
        mc.addAttr(
            aim_control,
            shortName="upperLidFollow",
            proxy=f"{eye_control}.upperLidFollow",
            k=True,
        )

        mc.addAttr(
            eye_control,
            shortName="lowerLidFollow",
            at="float",
            dv=self.option("Default Lower Lid Follow").get(),
            k=True,
        )
        mc.addAttr(
            aim_control,
            shortName="lowerLidFollow",
            proxy=f"{eye_control}.lowerLidFollow",
            k=True,
        )

        mc.addAttr(
            eye_control,
            shortName="horizontalLidFollow",
            at="float",
            dv=self.option("Default Horizontal Follow").get(),
            k=True,
        )
        mc.addAttr(
            aim_control,
            shortName="horizontalLidFollow",
            proxy=f"{eye_control}.horizontalLidFollow",
            k=True,
        )

        labels = ["Lower", "Upper"]
        inversions = [1, -1]

        horizontal_mutlipliers = {
            "Lower": f"{eye_control}.horizontalLidFollow",
            "Upper": f"{eye_control}.horizontalLidFollow",
        }

        vertical_mutlipliers = {
            "Lower": f"{eye_control}.lowerLidFollow",
            "Upper": f"{eye_control}.upperLidFollow",
        }

        for idx in range(len(labels)):

            label = labels[idx]
            inversion = inversions[idx]

            lid_driver_parent = mc.rename(
                mc.createNode("transform"),
                self.config.generate_name(
                    classification="zro",
                    description=f"{description}{label}LidDriver",
                    location=location,
                ),
            )

            lid_driver = mc.rename(
                mc.createNode("transform"),
                self.config.generate_name(
                    classification="mech",
                    description=f"{description}{label}LidDriver",
                    location=location,
                ),
            )

            lid_tracker = mc.rename(
                mc.createNode("transform"),
                self.config.generate_name(
                    classification="mech",
                    description=f"{description}{label}LidTracker",
                    location=location,
                ),
            )

            mc.parent(
                lid_driver_parent,
                component_org,
            )

            mc.parent(
                lid_driver,
                lid_driver_parent,
            )

            mc.parent(
                lid_tracker,
                lid_driver_parent,
            )
            mc.xform(
                lid_driver_parent,
                matrix=mc.xform(
                    eye_joint,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

            mc.parentConstraint(
                eye_control,
                lid_tracker,
                maintainOffset=True,
            )

            horizontal_multiplier = mc.createNode("floatMath")
            vertical_multiplier = mc.createNode("floatMath")
            blend_multiplier = mc.createNode("multiplyDivide")

            mc.setAttr(
                f"{horizontal_multiplier}.operation",
                2,  # -- Multiply
            )

            mc.setAttr(
                f"{vertical_multiplier}.operation",
                2,  # -- Multiply
            )

            mc.connectAttr(
                f"{lid_tracker}.rotate{up_axis}", # cross_axis
                f"{horizontal_multiplier}.floatA",
            )

            mc.connectAttr(
                f"{lid_tracker}.rotate{cross_axis}", # up_axis
                f"{vertical_multiplier}.floatA",
            )

            mc.connectAttr(
                horizontal_mutlipliers[label],
                f"{horizontal_multiplier}.floatB",
            )

            mc.connectAttr(
                vertical_mutlipliers[label],
                f"{vertical_multiplier}.floatB",
            )

            mc.connectAttr(
                f"{horizontal_multiplier}.outFloat",
                f"{blend_multiplier}.input1X",
            )

            mc.connectAttr(
                f"{vertical_multiplier}.outFloat",
                f"{blend_multiplier}.input1Y",
            )

            mc.connectAttr(
                f"{eye_control}.autoEyelids",
                f"{blend_multiplier}.input2X",
            )

            mc.connectAttr(
                f"{eye_control}.autoEyelids",
                f"{blend_multiplier}.input2Y",
            )

            mc.connectAttr(
                f"{blend_multiplier}.outputX",
                f"{lid_driver}.rotate{up_axis}", # cross_axis
            )

            mc.connectAttr(
                f"{blend_multiplier}.outputY",
                f"{lid_driver}.rotate{cross_axis}", # up_axis
            )

            lid_control = aniseed_toolkit.run(
                "Create Control",
                description=f"{label}EyeLid",
                location=location,
                parent=lid_driver,
                match_to=lid_driver,
                config=self.config,
                shape="core_cube",
            )

            kwargs = {
                forward_axis.lower(): 1,
                up_axis.lower(): 0.0,
                cross_axis.lower(): 0.5,
            }

            aniseed_toolkit.run(
                "Scale Shapes",
                lid_control.ctl,
                scale_by=1,
                **kwargs
            )

            kwargs = {
                forward_axis.lower(): 0.5,
                up_axis.lower(): 0.2 * (1 if label == "Upper" else -1),
                cross_axis.lower(): 0.0,
            }

            aniseed_toolkit.run(
                "Offset Shapes",
                lid_control.ctl,
                offset_by=1,
                **kwargs
            )
            mc.parentConstraint(
                lid_control.ctl, # lid_driver,
                self.input(f"{label} Eye Lid Joint").get(),
                maintainOffset=True,
            )

    @classmethod
    def axis_vector(cls, axis):
    
        if axis.lower() == "x":
            return [1, 0, 0]
    
        elif axis.lower() == "y":
            return [0, 1, 0]
    
        else:
            return [0, 0, 1]
