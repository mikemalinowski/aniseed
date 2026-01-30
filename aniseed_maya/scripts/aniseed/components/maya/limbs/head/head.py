import os
import aniseed
import aniseed_toolkit
import maya.cmds as mc


class HeadComponent(aniseed.RigComponent):
    """
    This is a very simple component which includes a single neck bone/control and
    a head bone/control in a linear hierarchy.
    """

    identifier = "Limb : Head"
    icon = os.path.join(
        os.path.dirname(__file__),
        "head.png",
    )

    def __init__(self, *args, **kwargs):
        super(HeadComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Neck Joints",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Head Joint",
            value="",
            validate=True,
            group="Required Joints"
        )

        self.declare_option(
            name="Description Prefix",
            value="",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Align Head To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Neck To World",
            value=True,
            group="Behaviour",
        )

        self.declare_output(
            "Neck Control",
        )

        self.declare_output(
            "Head Control",
        )

        # -- Declare our properties we will use during our build process
        self.neck_control = None
        self.head_control = None

    def input_widget(self, requirement_name):
        if requirement_name in ["Parent", "Neck Joint", "Head Joint"]:
            return aniseed.widgets.ObjectSelector(component=self)
        if requirement_name == "Neck Joints":
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name: str):
        if option_name in ["Location"]:
            return aniseed.widgets.ItemSelector(
                items=[
                    self.config.left,
                    self.config.middle,
                    self.config.right,
                ],
                default_item=self.config.middle,
            )

    def user_functions(self):
        return {
            "Create Joints": self.build_skeleton,
        }

    def run(self):

        neck_joints = self.input("Neck Joints").get()
        head_joint = self.input("Head Joint").get()

        prefix = self.option("Description Prefix").get()
        location = self.option("Location").get()

        neck_controls = []
        next_parent = self.input("Parent").get()

        for neck_joint in neck_joints:
            # -- Create the main hip control
            neck_control = aniseed_toolkit.run(
                "Create Control",
                description=f"{prefix}Neck",
                location=location,
                parent=next_parent,
                shape="core_circle",
                config=self.config,
                match_to=neck_joint,
                shape_scale=20.0,
            )

            if self.option("Align Neck To World").get():
                mc.xform(
                    neck_control.org,
                    rotation=[0, 0, 0],
                    worldSpace=True,
                )

            # -- Constrain our neck
            mc.parentConstraint(
                neck_control.ctl,
                neck_joint,
                maintainOffset=True,
            )

            mc.scaleConstraint(
                neck_control.ctl,
                neck_joint,
                maintainOffset=True,
            )
            neck_controls.append(neck_control)
            next_parent = neck_control.ctl

        # -- Create the main hip control
        head_control = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}Head",
            location=location,
            parent=next_parent,
            shape="core_lollipop",
            config=self.config,
            match_to=head_joint,
            shape_scale=30.0,
            rotate_shape=[90, 0, 0],
        )

        if self.option("Align Head To World").get():
            mc.xform(
                head_control.org,
                rotation=[0, 0, 0],
                worldSpace=True,
            )

        # -- Constrain the head joint
        mc.parentConstraint(
            head_control.ctl,
            head_joint,
            maintainOffset=True,
        )

        mc.scaleConstraint(
            head_control.ctl,
            head_joint,
            maintainOffset=True,
        )

        # -- Set our outputs
        self.output("Head Control").set(head_control.ctl)
        self.output("Neck Control").set(neck_controls[0].ctl)

    def build_skeleton(self):

        try:
            parent = mc.ls(sl=True)[0]

        except:
            parent = None

        joint_map = aniseed_toolkit.run(
            "Load Joints File",
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "head.json",
            ),
            apply_names=False,
            worldspace_root=True,
        )
        print(joint_map)
        location = self.option("Location").get()
        prefix = self.option("Description Prefix").get()

        neck = mc.rename(
            joint_map["JNT_Neck_01_MD"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{prefix}Neck",
                location=location
            ),
        )


        head = mc.rename(
            joint_map["JNT_Head_01_MD"],
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{prefix}Head",
                location=location
            ),
        )

        self.input("Neck Joints").set([neck])
        self.input("Head Joint").set(head)