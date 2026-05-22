import os
import mref
import snappy
import aniseed
import aniseed_toolkit
from maya import cmds


# noinspection PyInterpreter
class SimpleIKFKComponent(aniseed.RigComponent):
    identifier = "Mechanics : Two Bone IKFK"
    icon = os.path.join(
        os.path.dirname(__file__),
        "arm.png",
    )

    # noinspection PyUnresolvedReferences
    def __init__(self, *args, **kwargs):
        super(SimpleIKFKComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Root Joint",
            description="The root of the chain",
            validate=True,
            group="Required Joints"
        )

        self.declare_input(
            name="Tip Joint",
            description="The tip of the chain",
            validate=True,
            group="Required Joints"
        )

        self.declare_option(
            name="Descriptive Prefix",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            value=self.config.left,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Align IK To World",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Upvector To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Apply Soft Ik",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Apply World Fk Switches",
            value=True,
            group="Behaviour",
        )

        self.declare_output(
            name="Blended Upper",
        )

        self.declare_output(
            name="Blended Lower",
        )

        self.declare_output(
            name="Blended Tip",
        )

        # -- Declare our build properties - this is only required because i have
        # -- chosen within this component to break up the long build script
        # -- into functions, and therefore we use this to access items created
        # -- from other functions.
        self.prefix: str = ""
        self.location: str = ""
        self.org: str = ""
        self.joints: list[str] = []
        self.chain_direction: "Direction" = None
        self.config_control: "Control" = None
        self.upvector_control: "Control" = None
        self.ik_target_control: "Control" = None
        self.fk_upper_control: "Control" = None
        self.fk_lower_control: "Control" = None
        self.fk_end_control: "Control" = None

        self.controls: list[str] = []
        self.fk_controls: list[str] = []
        self.ik_controls: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [90, 0, 0]

    def on_enter_stack(self):
        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def option_widget(self, option_name: str):
        """
        This allows us to provide dedicate widgets for specific options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config, self.option(option_name).get())

    def input_widget(self, requirement_name):
        """
        This allows us to provide dedicate widgets for specific inputs
        """
        object_fields = [
            "Parent",
            "Root Joint",
            "Tip Joint",
        ]
        if requirement_name in object_fields:
            return aniseed.widgets.ObjectSelector(component=self)

        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector(component=self)

    def is_valid(self):

        arm_joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
        )[1:]

        direction = aniseed_toolkit.run(
            "Get Chain Facing Direction",
            arm_joints[0],
            arm_joints[-1],
        )

        if direction != direction.PositiveX and direction != direction.NegativeX:
            print("Validation Warning : Chain is not failing Up/Down X")
            print(f"    Tested Chain : {arm_joints}")
            print(direction)
            return False

        return True

    def run(self):
        """
        This is triggered when the stack is executed
        """
        self._clear_values()
        self.prefix = self.option('Descriptive Prefix').get()
        self.location = self.option("Location").get()

        self.org = aniseed_toolkit.transforms.create(
            classification=self.config.organisational,
            description=f"{self.prefix}Arm",
            location=self.location,
            config=self.config,
            parent=self.input("Parent").get(),
            match_to=self.input("Parent").get()
        )
        self.joints = aniseed_toolkit.joints.get_between(
            start=self.input('Root Joint').get(),
            end=self.input("Tip Joint").get(),
        )
        self._create_controls()

        ikfk_setup = aniseed_toolkit.rigging.create_two_bone_ikfk(
            parent=self.org,
            root_joint=self.joints[0],
            end_joint=self.joints[-1],
            attribute_host=self.config_control.ctl,
            attribute_name="ikfk",
            constrain=True,
            soft_ik=self.option("Apply Soft Ik").get(),
            soft_ik_host=self.ik_target_control.ctl,
        )

        # -- Create the guide line
        aniseed_toolkit.guide.link(
            self.upvector_control.ctl,
            ikfk_setup.ik_chain[1].name(),
        )

        for node in ikfk_setup.all_nodes():
            node.rename(
                self.config.generate_name(
                    classification="mech",
                    description=f"{self.prefix}{node.name()}",
                    location=self.location,
                ),
            )

        cmds.parentConstraint(
            self.ik_target_control.ctl,
            ikfk_setup.ik_target.name(),
            maintainOffset=True,
        )
        cmds.parentConstraint(
            self.upvector_control.ctl,
            ikfk_setup.ik_upvector.name(),
            maintainOffset=False,
        )

        for idx, fk_marker in enumerate(ikfk_setup.fk_chain):
            cmds.parentConstraint(
                self.fk_controls[idx],
                fk_marker.name(),
                maintainOffset=True,
            )

        # -- Hook up the visibility attributes
        ikfk_attribute = mref.get(f"{self.config_control.ctl}.ikfk")

        ik_condition = mref.create("lessThan")
        fk_condition = mref.create("greaterThan")

        ikfk_attribute.connect(ik_condition.input1)
        ikfk_attribute.connect(fk_condition.input1)

        ik_condition.input2.set(0.9)
        fk_condition.input2.set(0.1)
        ik_visibility_attribute = ik_condition.output.full_name()
        fk_visibility_attribute = fk_condition.output.full_name()

        for ik_control in self.ik_controls:
            ik_control = aniseed_toolkit.control.get(ik_control)
            cmds.connectAttr(
                ik_visibility_attribute,
                f"{ik_control.off}.visibility",
                force=True,
            )

        for fk_control in self.fk_controls:
            fk_control = aniseed_toolkit.control.get(fk_control)
            cmds.connectAttr(
                fk_visibility_attribute,
                f"{fk_control.off}.visibility",
                force=True,
            )

        # -- Set up the space switches on teh fk controls
        if self.option("Apply World Fk Switches").get():
            aniseed_toolkit.space.setup_fk_worldspace_switches(self.fk_controls, rig=self.rig)

        self.nk_joints = ikfk_setup.blend_chain.names()
        self._create_snap()
        self._set_outputs()

    def _create_controls(self):
        """
        Here we create all the controls for the arm
        """
        prefix = self.option('Descriptive Prefix').get()
        location = self.option("Location").get()

        # -- Add the configuration control
        self.config_control = aniseed_toolkit.control.create(
            description=f"{prefix}Config",
            location=location,
            parent=self.org,
            shape="core_lollipop",
            config=self.config,
            match_to=self.joints[0],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        self.fk_upper_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}UpperFK",
            location=self.location,
            parent=self.org,
            shape="core_paddle",
            config=self.config,
            match_to=self.joints[0],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        self.fk_lower_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}LowerFK",
            location=self.location,
            parent=self.fk_upper_control.ctl,
            shape="core_paddle",
            config=self.config,
            match_to=self.joints[1],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        self.fk_end_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}FK",
            location=self.location,
            parent=self.fk_lower_control.ctl,
            shape="core_paddle",
            config=self.config,
            match_to=self.joints[2],
            shape_scale=20.0,
            rotate_shape=self.shape_rotation,
        )

        # -- We'll iterate over our fk joints, so place them all in a list
        self.fk_controls = [
            self.fk_upper_control.ctl,
            self.fk_lower_control.ctl,
            self.fk_end_control.ctl,
        ]

        # -- Now create the main IK control
        self.ik_target_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}IK",
            location=self.location,
            parent=self.org,
            shape="core_stumpy_cross",
            config=self.config,
            match_to=self.joints[-1],
            shape_scale=20.0,
            rotate_shape=[-90, 0, 0],
        )
        self.ik_controls.append(self.ik_target_control.ctl)
        if self.option("Align IK To World").get():
            cmds.xform(
                self.ik_target_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- Create the upvector control for the arm
        self.upvector_control = aniseed_toolkit.control.create(
            description=f"{self.prefix}Upvector",
            location=self.location,
            parent=self.org,
            shape="core_sphere",
            config=self.config,
            match_to=self.joints[0],
            shape_scale=5.0,
            rotate_shape=None,
        )
        self.ik_controls.append(self.upvector_control.ctl)
        cmds.xform(
            self.upvector_control.org,
            translation=aniseed_toolkit.transformation.calculate_upvector_position(
                point_a=self.joints[0],
                point_b=self.joints[1],
                point_c=self.joints[2],
                length=1,
            ),
            worldSpace=True,
        )
        if self.option("Align Upvector To World").get():
            cmds.xform(
                self.upvector_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

    def _create_snap(self):
        group = "IKFK_Limb_%s_%s" % (
            self.prefix,
            self.location,
        )

        snappy.new(
            node=self.ik_target_control.ctl,
            target=self.nk_joints[2],
            group=group,
        )

        snappy.new(
            node=self.upvector_control.ctl,
            target=self.nk_joints[1],
            group=group,
        )

        snappy.new(
            node=self.fk_upper_control.ctl,
            target=self.nk_joints[0],
            group=group,
        )

        snappy.new(
            node=self.fk_lower_control.ctl,
            target=self.nk_joints[1],
            group=group,
        )

        snappy.new(
            node=self.fk_end_control.ctl,
            target=self.nk_joints[2],
            group=group,
        )

    def _set_outputs(self):

        self.output("Blended Upper").set(self.nk_joints[0])
        self.output("Blended Lower").set(self.nk_joints[1])
        self.output("Blended Tip").set(self.nk_joints[2])

    def _clear_values(self):

        self.prefix: str = ""
        self.location: str = ""
        self.org: str = ""
        self.joints: list[str] = []
        self.chain_direction: "Direction" = None
        self.config_control: "Control" = None
        self.upvector_control: "Control" = None
        self.ik_target_control: "Control" = None
        self.fk_upper_control: "Control" = None
        self.fk_lower_control: "Control" = None
        self.fk_end_control: "Control" = None

        self.controls: list[str] = []
        self.fk_controls: list[str] = []
        self.ik_controls: list[str] = []
        self.ik_joints: list[str] = []
        self.nk_joints: list[str] = []
        self.shape_rotation = [90, 0, 0]