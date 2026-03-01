"""
This plugin contains three different modules:

    Spline Spine: This contains any number of controls and joints
    Quad Spine: This contains specifically four controls, where the
        two inner controls are children of the respective outer controls.
    Tri Spline: This contains three primary controls where the central
        control moves automatically. There are an additional two controls
        which can be made visible by the animator to have it behave like
        a bezier curve.
"""
import os
import mref
import typing
import aniseed
import qtility
import aniseed_toolkit
from PySide6 import QtWidgets

from maya import cmds
import maya.api.OpenMaya as om


class SplineSpine(aniseed.RigComponent):
    """
    This is a spline setup with any number of controls and joints.
    """
    identifier = "Limb : Spline Spine"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(SplineSpine, self).__init__(*args, **kwargs)

        # -- Object Inputs
        self.declare_input(name="Parent", value="", group="Control Rig")
        self.declare_input(name="Root Joint", value="", group="Joint Requirements")
        self.declare_input(name="Tip Joint", value="", group="Joint Requirements")

        # -- Naming Options
        self.declare_option(name="Descriptive Prefix", value="Spine", group="Naming")
        self.declare_option(name="Location", value="md", group="Naming", pre_expose=True)

        # -- Visual Options
        self.declare_option(name="Shape", value="core_circle", group="Visuals")

        # -- Behavioural Options
        self.declare_option(name="Number Of Controls", value=4, group="Behaviour", pre_expose=True)
        self.declare_option(name="Orient Controls To World", value=True, group="Behaviour")
        self.declare_option(name="Lock End Orientations To Controls", value=True, group="Behaviour")
        self.declare_option(name="FK Interaction Mode", value=False, group="Behaviour")

        # -- Hidden Option (data storage)
        self.declare_option(name="GuideData", value=None, hidden=True)
        self.declare_option(name="Joint Count", value=8, hidden=False, pre_expose=True)
        self.declare_option(name="PreInitialised", value=False, hidden=True)

        # -- Outputs
        self.declare_output(name="Root Transform")
        self.declare_output(name="Tip Transform")
        self.declare_output(name="Master Control")
        self.declare_output(name="Root Control")
        self.declare_output(name="Tip Control")
        self.declare_output(name="Fk Tip")
        self.declare_output(name="Fk Root")

        # -- This component has a dynamic amount of resolved joints. Therefore
        # -- we want to ensure each joint is represented with an output attribute.
        # -- In order to do that we rebuild the output attributes whenever a
        # -- situation occurs which alters the joint count.
        self.input("Root Joint").value_changed.connect(self.update_outputs)
        self.input("Tip Joint").value_changed.connect(self.update_outputs)

    def on_build_started(self) -> None:
        """
        When the build starts, lets ensure any guides we have active
        are removed.
        """
        # -- Remove the guide if there is one
        if self.guide_data().get("LinkedGuide"):
            self.user_func_remove_guide()

        # -- Ensure our outputs are up to date
        self.update_outputs()

    def on_enter_stack(self) -> None:
        """
        When this enters the stack, if we were given a joint count then
        lets automatically generate the joints and build the guide
        """
        # -- We only ever want to do this once (i.e, we do not want to do
        # -- it when this is added to the stack via a load for instance).
        # -- Therefore we use a hidden option to store whether this has
        # -- already been performed or not.
        initialised_option = self.option("PreInitialised")

        # -- If this has already been performed, we skip
        if initialised_option.get():
            return

        # -- Now that we have used the joint count option we dont want
        # -- the user to see it again so we hide it. We also mark the
        # -- initialisation step as having run (so it never gets run again).
        self.option("Joint Count").set_hidden(True)
        initialised_option.set(True)

        # -- Providing the number of joints was not zero then we build
        # -- the joints and guide (the create guide is called from within
        # -- the create skeleton function.
        joint_count = self.option("Joint Count").get()
        if joint_count:
            self.user_func_create_skeleton(joint_count=joint_count)

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we need to remove the
        guide and bones too.
        """
        # -- Remove the guide
        self.user_func_remove_guide()

        # -- Remove the joints (re-parenting any children)
        new_parent = mref.get(self.input("Root Joint").get()).parent()
        aniseed_toolkit.joints.reparent_unknown_children(self.all_joints(), new_parent)

        # -- Now delete our leg chain and joints
        cmds.delete(self.input("Root Joint").get())

    def input_widget(self, requirement_name: str) -> QtWidgets.QWidget:
        """
        Return custom widgets for inputs that require it - for us in this case
        all our inputs are objects, so we just return the object selector always
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str) -> QtWidgets.QWidget:
        """
        This allows us to return different widgets for different options.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(self.option("Shape").get())

        if option_name == "Upvector Axis":
            return aniseed.widgets.AxisSelector()

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        This needs to return a dictionary which is used to generate
        a menu of callable items to for the user.
        """
        # -- This is our output variable
        menu = dict()

        # -- If we have no joints declared then we only expose the functionality
        # -- to create joints
        root_joint = self.input("Root Joint").get()
        if not root_joint or not cmds.objExists(root_joint):
            menu["Create Joints"] = self.user_func_create_skeleton
            return menu

        # -- To reach here we definitely have joints, so then we need to check
        # -- whether there is a guide in the scene or not.
        guide_data = self.guide_data()
        linked_guide = guide_data.get("LinkedGuide", "")

        # -- If there is a guide we give the ability to remove it, otherwise
        # -- we give the ability to create it.
        if linked_guide and cmds.objExists(linked_guide):
            menu["Remove Guide"] = self.user_func_remove_guide
            menu["Toggle Joint Selectability"] = self.user_func_toggle_joint_selectability
        else:
            menu["Create Guide"] = self.user_func_create_guide

        return menu

    def user_func_create_skeleton(self, joint_count=None, parent=None):
        """
        This function will build the joint chain for the user.
        """
        # -- Resolve the parent from the argument or the selection
        if not parent:
            selection = cmds.ls(selection=True)
            parent = selection[0] if selection else None

        # -- If we're not given a joint count then we need to
        # -- prompt for one
        joint_count = joint_count or int(
            qtility.request.text(
                title="Joint Count",
                message="How many joints do you want?"
            ),
        )
        joints = []
        if not joint_count or joint_count < 2:
            return

        # -- Resolve the translation increments for the joints based
        # -- on the expected guide data
        guide_height = self.guide_data()["control_transforms"][-1][-3]
        increment = guide_height / (joint_count - 1)
        running_parent = None

        # -- Now we cycle the joint count, creating each joint
        # -- in turn
        for idx in range(joint_count):
            joint = aniseed_toolkit.run(
                "Create Joint",
                description=self.option("Descriptive Prefix").get(),
                location=self.option("Location").get(),
                parent=running_parent,
                match_to=running_parent,
                config=self.config
            )

            # -- If this is not the first joint in the hierarchy
            # -- then we move it up in Y by the increment amount
            cmds.setAttr(f"{joint}.translateY", increment * (min(idx, 1)))

            # -- Store the joint and make this joint the parent
            # -- for the next joint to be made
            joints.append(joint)
            running_parent = joint

        # -- Parent the joint chain under the parent node
        if parent:
            cmds.parent(
                joints[0],
                parent,
            )

        # -- Set our outputs
        self.input("Root Joint").set(joints[0])
        self.input("Tip Joint").set(joints[-1])

        # -- As this component is always expected to be manipulated
        # -- via a guide, lets create the guide now
        guides = self.user_func_create_guide()

        # -- If we have a parent, then match the translation to it, this
        # -- just makes the riggers life a little easier as the component
        # -- will show in a contextually relevant locaiton.
        cmds.xform(
            guides[0],
            translation=cmds.xform(
            parent,
                query=True,
                translation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        # -- Add our joints to a deformers set.
        aniseed_toolkit.sets.add_to(joints, set_name="deformers")

    def user_func_toggle_joint_selectability(self):
        joints = self.all_joints()
        if aniseed_toolkit.joints.is_referenced(joints[0]):
            aniseed_toolkit.joints.unreference(joints)
        else:
            aniseed_toolkit.joints.make_referenced(joints)

    def is_valid(self) -> bool:
        """
        In this function we test the state of the component before we build
        """
        # -- To be valid we expect the root and tip to be
        # -- provided
        root_joint = self.input("Root Joint").get()
        tip_joint = self.input("Tip Joint").get()

        if not root_joint or not cmds.objExists(root_joint):
            print("No root joint specified")
            return False

        if not tip_joint or not cmds.objExists(tip_joint):
            print("No tip joint specified")
            return False

        return True

    def run(self):
        """
        This is where we build the actual rig
        """
        # -- Get our inputs
        start_joint = self.input("Root Joint").get()
        end_joint = self.input("Tip Joint").get()
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        orient_to_world = self.option("Orient Controls To World").get()
        control_scale = 10

        # -- Read the joints between
        joints = self.all_joints()

        # -- Create a basic transform node to act as the parent
        # -- of everything
        org = aniseed_toolkit.transforms.create(
            classification="org",
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            config=self.config,
            parent=self.input("Parent").get(),
            match_to=self.input("Parent").get(),
        )

        # -- Construct the spline setup. This returns a special spline
        # -- class we can use to get access to all the different objects.
        spline_setup = self._create_spline_setup(joints, parent=org, constrain=False)

        # -- Build the main master control
        master_control = aniseed_toolkit.control.create(
            description=f"{descriptive}Master",
            location=location,
            parent=org,
            shape=self.option("Shape").get(),
            shape_scale=control_scale * 1.25,
            config=self.config,
            match_to=spline_setup.out_controls[0].full_name(),
        )

        # -- If we need to orient it to the world then we do so by
        # -- adjusting the rotation of the org node
        if orient_to_world:
            cmds.xform(
                master_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- Add the FK and Ik Visibility Attributes
        cmds.addAttr(
            master_control.ctl,
            shortName="ik_visibility",
            attributeType="bool",
            defaultValue=True,
            keyable=True,
        )
        cmds.addAttr(
            master_control.ctl,
            shortName="fk_visibility",
            attributeType="bool",
            defaultValue=False,
            keyable=True,
        )

        # -- Create the IK controls
        ik_controls = self.setup_ik_controls(
            master_control,
            spline_setup,
            spline_setup.out_no_xform_org,
        )

        # -- Now create the Fk control setup
        fk_controls = self.create_fk(org, spline_setup)

        # -- Constrain the joints to the Fk controls. This is because the fk
        # -- setup is designed to follow the ik setup all the time.
        for idx in range(len(fk_controls)):

            fk_control = mref.get(fk_controls[idx].ctl)
            joint = mref.get(joints[idx])

            cmds.parentConstraint(
                fk_control.full_name(),
                joint.full_name(),
                maintainOffset=True,
            )
            cmds.scaleConstraint(
                fk_control.full_name(),
                joint.full_name(),
                maintainOffset=True,
            )

            # -- Hook up the visibility
            for nurbs_shape in fk_control.shapes():
                cmds.connectAttr(
                    f"{master_control.ctl}.fk_visibility",
                    f"{nurbs_shape.full_name()}.visibility",
                )

        for ik_control in ik_controls:
            ik_control = mref.get(ik_control.ctl)
            for nurbs_shape in ik_control.shapes():
                cmds.connectAttr(
                    f"{master_control.ctl}.ik_visibility",
                    f"{nurbs_shape.full_name()}.visibility",
                )

        # -- Finally we set our output variables
        self.output("Root Transform").set(spline_setup.out_trace_joints[0].name())
        self.output("Tip Transform").set(spline_setup.out_trace_joints[-1].name())
        self.output("Master Control").set(master_control.ctl)
        self.output("Fk Root").set(fk_controls[0].ctl)
        self.output("Fk Tip").set(fk_controls[-1].ctl)

    def setup_ik_controls(self, master_control, spline_setup, no_transform_node):
        """
        This will construct the IK controls for the rig
        """
        # -- Read out the option data we will need
        number_of_controls = self.option("Number Of Controls").get()
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        orient_to_world = self.option("Orient Controls To World").get()
        control_scale = 10

        # -- Define our running parent
        parent = master_control.ctl

        # -- We need to keep track of the ik controls we build
        ik_controls = []

        for idx in range(number_of_controls):

            # -- Construct a control and a tweaker. The tweaker is just
            # -- a child control - but it never acts as a parent. Its a nice
            # -- way to allow an animator to be able to adjust a single control
            # -- without affecting any of its children.
            base_control, base_control_tweaker = self.create_doubled_control(
                descriptive=descriptive,
                location=location,
                parent=parent,
                shape_scale=control_scale,
                match_to=spline_setup.out_controls[idx].full_name(),
                orient_to_world=orient_to_world,
                drive_this=spline_setup.out_controls[idx].full_name(),
            )

            # -- If we need to orient to world then we do that by adjusting
            # -- the rotation of the control org.
            if orient_to_world:
                cmds.xform(
                    base_control.org,
                    rotation=(0, 0, 0),
                    worldSpace=True,
                )

            # -- Store these controls as a pair
            ik_controls.extend([base_control, base_control_tweaker])

            # -- If we're building in FK interaction mode, then we place the ik
            # -- controls in an fk hierarchy. If not we leave them as children
            # -- of the master.
            if self.option("FK Interaction Mode").get():
                parent = base_control.ctl

        # -- Fill in the ik control outputs
        self.output("Root Control").set(ik_controls[1].ctl)
        self.output("Tip Control").set(ik_controls[-1].ctl)

        return ik_controls

    def create_fk(self, parent, spline_setup):
        """
        Creates our FK controllers
        """
        # -- Read out our option data
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        orient_to_world = self.option("Orient Controls To World").get()

        # -- Determine our default control size (maybe we can get this
        # -- dynamically by reading the length of the chain and dividing
        # -- it by the joint count?)
        control_scale = 10

        # -- We want our hierarchy to be fk - so we need to track the
        # -- parent on each iteration
        next_parent = spline_setup.out_org.full_name()

        # -- This is where we will store the output
        fk_controls = []

        for idx, trace_joint in enumerate(spline_setup.out_anchor_points):

            # -- Create the actual control hierarcy
            fk_control = aniseed_toolkit.control.create(
                description=f"{descriptive}Fk",
                location=location,
                parent=next_parent,
                shape=self.option("Shape").get(),
                shape_scale=control_scale,
                config=self.config,
                match_to=trace_joint.full_name(),
            )

            # -- We need the automated FK setup in the spline rig to
            # -- drive our FK controls. This is because the FK controls
            # -- in the spline rig auto-follow the IK.
            decompose_node = cmds.createNode("decomposeMatrix")
            cmds.connectAttr(f"{trace_joint.full_name()}.matrix", f"{decompose_node}.inputMatrix")
            cmds.connectAttr(f"{decompose_node}.outputTranslate", f"{fk_control.org}.translate")
            cmds.connectAttr(f"{decompose_node}.outputRotate", f"{fk_control.org}.rotate")
            cmds.connectAttr(f"{decompose_node}.outputScale", f"{fk_control.org}.scale")

            # -- Set the corresponding output plug
            tag = "FK Control %s" % idx
            self.output(tag).set(fk_control.ctl)

            # -- Store the fk control and make this fk control the parent
            # -- of the next fk control.
            fk_controls.append(fk_control)
            next_parent = fk_control.ctl

        return fk_controls

    def create_doubled_control(self, descriptive, location, parent, shape_scale, match_to, orient_to_world, drive_this):
        """
        This is a convenience function for creating two controls that sit atop of
        each other. This is useful for creating hierarchies of controls where
        each control has a sub control which can be manipulated in isolation.
        """
        main_control = aniseed_toolkit.control.create(
            description=descriptive,
            location=location,
            parent=parent,
            shape=self.option("Shape").get(),
            shape_scale=shape_scale,
            config=self.config,
            match_to=match_to,
        )
        tweak_control = aniseed_toolkit.control.create(
            description=f"{descriptive}Tweak",
            location=location,
            parent=main_control.ctl,
            shape=self.option("Shape").get(),
            shape_scale=shape_scale * 0.75,
            config=self.config,
            match_to=match_to,
        )
        if orient_to_world:
            cmds.xform(
                main_control.org,
                rotation=(0, 0, 0),
                worldSpace=True,
            )

        # -- if we're given something to drive, then we constrain that item
        # -- to the tweaker
        cmds.parentConstraint(
            tweak_control.ctl,
            drive_this,
            maintainOffset=True,
        )

        # -- As we're made up of a pair of controls, we return
        # -- a list of them both.
        return [
            main_control,
            tweak_control,
        ]

    def user_func_create_guide(self):
        """
        This function will create the guide setup
        """

        # -- Check if the guide already exists first
        guide = self.guide_data().get("LinkedGuide")
        if guide and cmds.objExists(guide):
            return []

        # -- Read the joint chain
        joints = self.all_joints()

        # -- Make the joints unselectable
        aniseed_toolkit.joints.make_referenced(joints)

        # -- Create the spline setup - note that this same function is called
        # -- when building the rig too. This ensures the behaviour of the guide
        # -- and the rig are the same
        spline_setup = self._create_spline_setup(joints=joints)

        # -- Create a node to parent everything under.
        guide_org = cmds.createNode(
            "transform",
            name="splineGuide",
        )
        spline_setup.out_org.set_parent(guide_org)

        # -- We now need to build actual guide objects to drive our
        # -- spline spine. These guides will be FK
        guides = self.create_guide_controls(guide_org, spline_setup)

        for guide in guides:
            aniseed_toolkit.run("Tag Node", guide, "ControlGuide")

        # -- Now that we have built the guide we need to store
        # -- the reference to the guide node in the guide data.
        guide_data = self.guide_data()
        guide_data["LinkedGuide"] = guide_org
        self.option("GuideData").set(guide_data)

        # -- If there is a parent of the root then we constrain our
        # -- setup to that
        root_joint = mref.get(joints[0])
        if root_joint.parent():
            cmds.parentConstraint(
                root_joint.parent().full_name(),
                guide_org,
                maintainOffset=True,
            )

        return guides

    def create_guide_controls(self, guide_org, spline_setup):
        """
        This function will cycle over the controllable items in the spline
        setup and create a guide control for each.
        """
        guides = []
        parent = guide_org
        for control_transform in spline_setup.out_controls:
            guides.append(
                aniseed_toolkit.run(
                    "Create Guide",
                    joint=control_transform.name(),
                    parent=parent,
                ),
            )
            parent=guides[-1]
        return guides


    def user_func_remove_guide(self):
        """
        This will serialise the guide information (allowing the spline to be
        rebuilt from that data later), and then remove the spline setup.
        """
        if not self.has_guide():
            return

        # -- Make the joints selectable
        joints = self.all_joints()
        aniseed_toolkit.joints.unreference(joints)

        # -- Mark this as not having an active guide
        guide_data = self.guide_data()

        # -- Validation check for legacy or broken guide data
        if not "control_transforms" in guide_data:
            guide_data = self.default_guide_data()

        # -- Store the guide data
        root_joint = self.input("Root Joint").get()
        guide_root = guide_data["LinkedGuide"]

        # -- Define the list of control transforms we will store
        guide_data["control_transforms"] = []

        # -- Get all the controllable items
        guide_controls = aniseed_toolkit.tagging.all_children(guide_root, "ControlGuide")

        # -- Now we cycle them and store the relative matrix between the
        # -- guide and the root joint. This means that everything can be
        # -- rebuilt relative to the root joint.
        for guide_control in sorted(guide_controls):
            root_relative_matrix = aniseed_toolkit.run(
                "Get Relative Matrix",
                guide_control,
                root_joint,
            )
            guide_data["control_transforms"].append(root_relative_matrix)

        # -- Now delete the spline setup
        with aniseed_toolkit.joints.HeldTransforms(joints):
            cmds.delete(str(guide_data["LinkedGuide"]))

        # -- Finally we remove the entry for the linked guide and we
        # -- store the updated guide information.
        guide_data["LinkedGuide"] = ""
        self.option("GuideData").set(guide_data)


    def _create_spline_setup(self, joints, parent=None, constrain=True):
        """
        This is called by both the guide and the rig build process, as much of
        the result is common between the two
        """
        # -- Read out the option data
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Read out the guide data
        guide_data = self.guide_data()

        # -- We need to give the spline builder the general parent transform
        # -- for all the local matrices - so for us, this is our root joint
        # -- transform
        root_matrix = cmds.xform(
            self.input("Root Joint").get(),
            matrix=True,
            worldSpace=True,
            query=True,
        )

        # -- Build the spline setup. This returns a SplineSetup class which
        # -- gives us access to all the items it has built for us.
        spline_setup = aniseed_toolkit.run(
            "Create Spline Setup",
            parent=parent,
            joints=joints,
            org_transform=root_matrix,
            control_transforms=guide_data["control_transforms"],
            constrain=constrain,
            lock_end_orientations=self.option("Lock End Orientations To Controls").get(),
        )

        # -- Now we just need to name all the items in the spline setup
        # -- based upon our rigging config.
        spline_setup.out_org.rename(
            self.config.generate_name(
                classification="org",
                description=f"{descriptive}SplineSolve",
                location=location,
            )
        )

        # -- Name all the control elements
        for control in spline_setup.out_controls:
            control.rename(
                self.config.generate_name(
                    classification="loc",
                    description=f"{descriptive}PointTransform",
                    location=location,
                )
            )

        for upvector in spline_setup.out_upvectors:
            upvector.rename(
                self.config.generate_name(
                    classification="loc",
                    description=f"{descriptive}UpvectorTransform",
                    location=location,
                )
            )
        for cluster in spline_setup.out_clusters:
            cluster.rename(
                self.config.generate_name(
                    classification="cls",
                    description=f"{descriptive}ClusterTransform",
                    location=location,
                )
            )

        for joint in spline_setup.out_trace_joints:
            joint.rename(
                self.config.generate_name(
                    classification="jnt",
                    description=f"{descriptive}Tracer",
                    location=location,
                )
            )

        for joint in spline_setup.out_anchor_points:
            joint.rename(
                self.config.generate_name(
                    classification="jnt",
                    description=f"{descriptive}Anchor",
                    location=location,
                )
            )

        spline_setup.out_no_xform_org.rename(
            self.config.generate_name(
                classification="org",
                description=f"{descriptive}NoTransform",
                location=location,
            )
        )
        return spline_setup

    def guide_data(self):
        """
        This is a convenience function for returning the guide data, but if
        that data has not yet been set then it will generate default guide
        data.
        """
        data = self.option("GuideData").get()
        return data or self.default_guide_data()

    def default_guide_data(self):
        """
        The first time this component is generated we need to build some default
        guide data. This ensures our code paths can always assume they have access
        to guide data.
        """
        # --
        base_number = 50.0
        identity_matrix = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]

        data = dict(
            control_transforms=[],
            LinkedGuide="",
        )

        control_count = self.option("Number Of Controls").get()
        increment = base_number / (control_count - 1)
        for idx in range(control_count):
            matrix = identity_matrix[:]
            matrix[-3] = increment * idx
            data["control_transforms"].append(matrix)

        return data

    def all_joints(self):
        return aniseed_toolkit.joints.get_between(
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
        )

    def has_guide(self):
        """
        Checks whether this has a valid guide or not
        """
        # -- Check if the guide already exists first
        guide = self.guide_data().get("LinkedGuide")
        if guide and cmds.objExists(guide):
            return True

        return False

    def update_outputs(self) -> None:
        """
        This function is called whenever the start or end joint is changed. We
        use this to count the amount of joints which will be created and ensure
        that each one is represented by an output pin.
        This ensures we are supporting a dynamic number of output attributes based
        on the inputs.
        """
        # -- Start by removing all our output attributes
        for output_plug in self.outputs()[:]:
            if output_plug.name().startswith("FK Control"):
                self.remove_output(output_plug.name())

        # -- Attempt to get the joints. Note that this is wrapped in an exception
        # -- statement, as its possible one or more of these attributes are blank.
        try:
            joints = aniseed_toolkit.run(
                "Get Joints Between",
                self.input("Root Joint").get(),
                self.input("Tip Joint").get(),
            )
        except:
            joints = []
        print("found joints : %s" % joints)
        # -- We now cycle the joints and declare a new output attribute
        # -- to represent it
        for idx, joint in enumerate(joints):
            self.declare_output(name="FK Control %s" % idx)

class QuadSplineSpine(SplineSpine):
    """
    This is a spline solve with four controls. The outer controls (the Hip and
    the Chest) and then two inner controls (each a child of their respective
    outer controls).
    """
    identifier = "Limb : Spline Spine (Quad)"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(QuadSplineSpine, self).__init__(*args, **kwargs)

        # -- In the quad setup we're locked specifically to four
        # -- controls.
        self.option("Number Of Controls").set(4)
        self.option("Number Of Controls").set_hidden(True)
        self.option("FK Interaction Mode").set_hidden(True)

    def setup_ik_controls(self, master_control, spline_setup, no_transform_node):
        """
        We inherit from the main spline component, but we have a different
        hierarchical structure to our controls.
        """
        # -- Read our option data
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        orient_to_world = self.option("Orient Controls To World").get()
        control_scale = 10

        # -- We need to return the list of controls we create, so we
        # -- define a variable for that
        ik_controls = []

        # -- Create the hip
        base_control, base_control_tweaker = self.create_doubled_control(
            descriptive=f"{descriptive}Hip",
            location=location,
            parent=master_control.ctl,
            shape_scale=control_scale * 1.1,
            match_to=spline_setup.out_controls[0].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[0].full_name(),
        )
        ik_controls.extend([base_control, base_control_tweaker])

        lower_mid_control, lower_mid_control_tweaker = self.create_doubled_control(
            descriptive=descriptive,
            location=location,
            parent=base_control.ctl,
            shape_scale=control_scale,
            match_to=spline_setup.out_controls[1].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[1].full_name(),
        )
        ik_controls.extend([lower_mid_control, lower_mid_control_tweaker])

        chest_control, chest_control_tweaker = self.create_doubled_control(
            descriptive=f"{descriptive}Chest",
            location=location,
            parent=master_control.ctl,
            shape_scale=control_scale,
            match_to=spline_setup.out_controls[3].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[3].full_name(),
        )
        ik_controls.extend([chest_control, chest_control_tweaker])

        upper_mid_control, upper_mid_control_tweaker = self.create_doubled_control(
            descriptive=descriptive,
            location=location,
            parent=chest_control.ctl,
            shape_scale=control_scale,
            match_to=spline_setup.out_controls[2].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[2].full_name(),
        )
        ik_controls.extend([upper_mid_control, upper_mid_control_tweaker])

        # -- Now our controls are created we can set our outputs
        self.output("Root Control").set(base_control_tweaker.ctl)
        self.output("Tip Control").set(chest_control_tweaker.ctl)

        return ik_controls


class TriSplineSpine(SplineSpine):
    """
    This is a spline component which is driven by three main controls, with
    the center control being automatic in movement. There are a further two
    hidden controls which are children of the center control which allows for
    a bezier style of manipulation.
    """
    identifier = "Limb : Spline Spine (Tri)"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    def __init__(self, *args, **kwargs):
        super(TriSplineSpine, self).__init__(*args, **kwargs)

        # -- This component as a new option to define the cross vector
        # -- of the ribbon (that is the direction the width should be in).
        self.declare_option(
            name="Ribbon Cross Vector",
            value=[1, 0, 0],
        )

        # -- Force this component to use three controls and do
        # -- not expose it to the user
        self.option("Number Of Controls").set(5)
        self.option("Number Of Controls").set_hidden(True)

    def option_widget(self, option_name: str):
        """
        Return a specific widget for the vector option.
        """
        if option_name == "Ribbon Cross Vector":
            return aniseed.widgets.VectorWidget()
        return super(TriSplineSpine, self).option_widget(option_name)

    def user_func_create_guide(self):
        """
        We want a more bespoke guide hierarchy for our tri component
        """
        # -- Check if the guide already exists first
        if self.has_guide():
            return []

        guides = super(TriSplineSpine, self).user_func_create_guide()
        cmds.parent(guides[2], guides[0])
        cmds.parent(guides[-1], guides[0])
        return guides

    def setup_ik_controls(self, master_control, spline_setup, no_transform_node):
        """
        This is where the main difference is between the tri component and the
        standard component.
        """
        # -- We need to return the controls we create - so start by defining
        # -- that variable
        ik_controls = []

        # -- Read our options and inputs.
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        orient_to_world = self.option("Orient Controls To World").get()
        control_scale = 10.0

        # -- Now we can start building our actual controls.
        hip_control, hip_control_tweaker = self.create_doubled_control(
            descriptive=f"{descriptive}Hip",
            location=location,
            parent=master_control.ctl,
            shape_scale=control_scale * 1.1,
            match_to=spline_setup.out_controls[0].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[0].full_name(),
        )
        ik_controls.extend([hip_control, hip_control_tweaker])

        mid_control, mid_control_tweaker = self.create_doubled_control(
            descriptive=f"{descriptive}Mid",
            location=location,
            parent=master_control.ctl,
            shape_scale=control_scale * 0.9,
            match_to=spline_setup.out_controls[2].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[2].full_name(),
        )
        cmds.addAttr(
            mid_control.ctl,
            shortName="ShowMidPointControls",
            attributeType="bool",
            defaultValue=False,
            keyable=True,
        )
        ik_controls.extend([mid_control, mid_control_tweaker])

        upper_mid_control, upper_mid_control_tweaker = self.create_doubled_control(
            descriptive=f"{descriptive}UpperMid",
            location=location,
            parent=mid_control_tweaker.ctl,
            shape_scale=control_scale * 0.9,
            match_to=spline_setup.out_controls[3].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[3].full_name(),
        )
        cmds.connectAttr(f"{mid_control.ctl}.ShowMidPointControls", f"{upper_mid_control.org}.visibility")
        ik_controls.extend([upper_mid_control, upper_mid_control_tweaker])

        lower_mid_control, lower_mid_control_tweaker = self.create_doubled_control(
            descriptive=f"{descriptive}LowerMid",
            location=location,
            parent=mid_control_tweaker.ctl,
            shape_scale=control_scale * 0.9,
            match_to=spline_setup.out_controls[1].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[1].full_name(),
        )
        cmds.connectAttr(f"{mid_control.ctl}.ShowMidPointControls", f"{lower_mid_control.org}.visibility")
        ik_controls.extend([lower_mid_control, lower_mid_control_tweaker])

        chest_control, chest_control_tweaker = self.create_doubled_control(
            descriptive=f"{descriptive}Chest",
            location=location,
            parent=master_control.ctl,
            shape_scale=control_scale * 1.1,
            match_to=spline_setup.out_controls[4].full_name(),
            orient_to_world=orient_to_world,
            drive_this=spline_setup.out_controls[4].full_name(),
        )
        ik_controls.extend([chest_control, chest_control_tweaker])

        # -- We use a skinned mesh to automate the movement of the
        # -- central control, so lets build that now.
        self.setup_auto_ribbon(
            hip_control.ctl,
            mid_control.org,
            chest_control.ctl,
            no_transform_node,
        )

        # -- Finally we set the outputs to our new controls and return
        # -- the created controls.
        self.output("Root Control").set(ik_controls[1].ctl)
        self.output("Tip Control").set(ik_controls[-1].ctl)
        return ik_controls

    def setup_auto_ribbon(self, bottom_control, mid_control, top_control, no_transform_node):
        """
        This will generate a ribbon mesh and have the mid control follow that
        newly created mesh.
        """
        # -- We need to start by creating a specific set of joints which we will
        # -- skin our ribbon to.
        top_joint = mref.create("joint", parent=top_control)
        top_joint.rename(
            self.config.generate_name(
                classification=self.config.mechanical,
                description="AutoRibbonTop",
                location=self.option("Location").get(),
            )
        )
        top_joint.match_to(mref.get(top_control))

        # -- Now create the second joint. At this point we have a joint to
        # -- follow the top control and a joint to follow the bottom control.
        bottom_joint = mref.create("joint", parent=bottom_control)
        bottom_joint.rename(
            self.config.generate_name(
                classification=self.config.mechanical,
                description="AutoRibbonBottom",
                location=self.option("Location").get(),
            )
        )
        bottom_joint.match_to(mref.get(bottom_control))

        # -- Now we can build the actual geometry. As we will skin this mesh it
        # -- is important that it does not get transformed - so we place it under the
        # -- no transform node.
        mesh = self.generate_ribbon_mesh(bottom_control, mid_control, top_control)
        cmds.parent(mesh, no_transform_node.full_name())

        # -- Skin the mesh to the two joints we created.
        skin = cmds.skinCluster(
            [
                top_joint.full_name(),
                bottom_joint.full_name(),
                mesh,
            ],
            bindMethod=0,
            skinMethod=0,
            ignoreHierarchy=True,
        )[0]

        # -- Now we need to be specific about the weighting. We want the
        # -- weighting of the end-point verticed to be 100% to their respective
        # -- bones, but the mid point vertices to be 50/50 between the two.
        cmds.skinPercent(skin, f"{mesh}.vtx[0:1]", transformValue=[(bottom_joint.full_name(), 1.0)])
        cmds.skinPercent(skin, f"{mesh}.vtx[2:5]", transformValue=[(bottom_joint.full_name(), 0.5), (top_joint.full_name(), 0.5)])
        cmds.skinPercent(skin, f"{mesh}.vtx[6:7]", transformValue=[(top_joint.full_name(), 1.0)])

        # -- Finally we need to setup the constraint for the mid control such
        # -- that it follows the ribbon.
        self.constrain_to_midpoint_vertex(
            mesh=mesh,
            transform=mid_control,
        )

    def generate_ribbon_mesh(self, top, middle, bottom, width=1.0, name="mesh_strip"):
        """
        Builds a 2-quad poly strip aligned to three transforms.
        Bottom edge = t1
        Middle edge = t2
        Top edge = t3
        
        Width is measured across each transform's local X axis.
        """
        # -- Read our option data
        cross_vector = self.option("Ribbon Cross Vector").get()

        # -- Construct a list of out three transforms
        transforms = [top, middle, bottom]

        # -- Determine the half width of the mesh
        half_width = width * 0.5

        # -- We will use the constructed points to build
        # -- the faces, so track them here
        points = []
    
        for transform in transforms:

            # -- Get the world matrix of the object
            m = om.MMatrix(cmds.xform(transform, query=True, worldSpace=True, matrix=True))
            tm = om.MTransformationMatrix(m)
    
            # -- Extract the world position
            pos = tm.translation(om.MSpace.kWorld)
    
            # -- Get the cross axis
            axis = om.MVector(*cross_vector) * m
            axis.normalize()

            # -- Calculate the left and right position
            left = pos - (axis * half_width)
            right = pos + (axis * half_width)

            # -- Store the two points.
            points.append(left)
            points.append(right)

        # -- Now we construct the vertex array
        verts = [(p.x, p.y, p.z) for p in points]

        # -- And finally construct the face array
        faces = [
            [0, 1, 3, 2],  # bottom quad
            [2, 3, 5, 4],  # top quad
        ]

        # -- With all this information we can construct our two
        # -- polygons.
        mesh = cmds.polyCreateFacet(point=[verts[i] for i in faces[0]], name=name)[0]
        cmds.polyAppendVertex(mesh, append=[verts[i] for i in faces[1]])

        return mesh

    def constrain_to_midpoint_vertex(self, mesh, transform):
        """
        Here we need to make the given trasnform follow the vertices in the middle
        of the ribbon mesh
        """
        # -- Get the transform as a reference object
        transform = mref.get(transform)

        # -- Create a transform and set it to be a child of the transform's parent
        buffer = mref.create(
            "transform",
            name=self.config.generate_name(
                classification=self.config.mechanical,
                description="MidPointTracker",
                location=self.option("Location").get(),
            ),
        )
        buffer.set_parent(transform.parent())

        # -- Set up the geometry contraint
        u_value = self.get_surface_u_from_vertex(f"{mesh}.vtx[5]")
        constraint = cmds.pointOnPolyConstraint(mesh, buffer.full_name(), maintainOffset=False)[0]
        cmds.setAttr(f"{constraint}.mesh_stripU0", 1)
        cmds.setAttr(f"{constraint}.mesh_stripV0", 0.5)

        # -- Finally we need the transform node to now be a child
        # -- of our created buffer.
        transform.set_parent(buffer)
        return constraint

    def get_surface_u_from_vertex(self, vertex):
        """
        Returns the pointOnPoly-style (u, v) for a vertex
        relative to its closest face.
        """
        # -- Read out the mesh name
        mesh = vertex.split('.')[0]

        # -- Get the position of the vertex in worldspace
        pos = cmds.pointPosition(vertex, world=True)

        # -- Use the closestPointOnMesh node to calculate the u value. Note
        # -- that this will then be deleted after we read the value we need
        cpm = cmds.createNode("closestPointOnMesh")
        cmds.connectAttr(mesh + ".worldMesh[0]", cpm + ".inMesh", force=True)
        cmds.setAttr(cpm + ".inPosition", pos[0], pos[1], pos[2], type="double3")

        # -- Read the u value
        face_index = cmds.getAttr(cpm + ".closestFaceIndex")
        u = cmds.getAttr(cpm + ".parameterU")

        # -- Clean up by removing the node
        cmds.delete(cpm)

        return u

    def create_guide_controls(self, guide_org, spline_setup):
        """
        We want our guides to be in a flat hierarcy
        """
        # -- We need to return a list of created guides
        # -- so declare that now
        guides = []

        # -- Cycle the transformable nodes and create a guide
        # -- for each one
        for control_transform in spline_setup.out_controls:
            guides.append(
                aniseed_toolkit.run(
                    "Create Guide",
                    joint=control_transform.name(),
                    parent=guide_org,
                ),
            )

        # -- Set the parenting for the guides
        cmds.parent(guides[1], guides[2])
        cmds.parent(guides[3], guides[2])
        return guides
