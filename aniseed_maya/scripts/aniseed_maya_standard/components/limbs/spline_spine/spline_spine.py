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
import logging
import copy
import mref
import typing
import aniseed
import qtility
import aniseed_toolkit
from PySide6 import QtWidgets

import maya.api.OpenMaya as om
from aniseed_maya_standard.mixins import MirrorMixin

log = logging.getLogger(__name__)


class SplineSpine(aniseed.RigComponent, MirrorMixin):
    """
    This is a spline setup with any number of controls and joints.
    """
    identifier = "Limb : Spline Spine"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )

    # -- The default size of the controls
    control_scale = 10

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, master transform and root/tip joint inputs, the
        naming, visual and behavioural options (including the pre-exposed joint
        and control counts) and the transform/control outputs. Per-joint outputs
        are rebuilt whenever the root or tip joint input changes.
        """
        super().__init__(*args, **kwargs)

        # -- Object Inputs
        self.declare_input(name="Parent", value="", group="Control Rig")
        self.declare_input(name="Spine Master Transform", value="", group="Control Rig", validate=False)

        self.declare_input(name="Root Joint", value="", group="Joint Requirements")
        self.declare_input(name="Tip Joint", value="", group="Joint Requirements")

        # -- Naming Options
        self.declare_option(name="Descriptive Prefix", value="Spine", group="Naming", pre_expose=True)
        self.declare_option(name="Location", value=self.config.middle, group="Naming", pre_expose=True)

        # -- Visual Options
        self.declare_option(name="Shape", value="core_circle", group="Visuals")

        # -- Behavioural Options
        self.declare_option(name="Number Of Controls", value=4, group="Behaviour", pre_expose=True)
        self.declare_option(name="Orient Controls To World", value=True, group="Behaviour")
        self.declare_option(name="Orient FK Controls To World", value=False, group="Behaviour")
        self.declare_option(name="Lock End Orientations To Controls", value=True, group="Behaviour")
        self.declare_option(name="FK Interaction Mode", value=False, group="Behaviour")
        self.declare_option(name="Invalidate First Fk Control", value=False, group="Behaviour")
        self.declare_option(name="Default Ik Tweak Visibility", value=True, group="Behaviour")
        self.declare_option(name="Show First Fk Offset Control", value=True, group="Behaviour")
        self.declare_option(name="Align Offsets To Bone", value=False, group="Behaviour")

        # -- Hidden Option (data storage)
        self.declare_option(name="GuideData", value=None, hidden=True)
        self.declare_option(name="Joint Count", value=8, hidden=False, pre_expose=True)

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
        # -- Now that we have used the joint count option we dont want
        # -- the user to see it again so we hide it.
        self.option("Joint Count").set_hidden(True)

        # -- Providing the number of joints was not zero then we build
        # -- the joints and guide (the create guide is called from within
        # -- the create skeleton function.
        joint_count = self.option("Joint Count").get()
        if joint_count:
            self.user_func_create_skeleton(joint_count=joint_count)

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def on_removed_from_stack(self):
        """
        When the component is removed from the stack we need to remove the
        guide and bones too.
        """
        # -- Remove the guide
        self.user_func_remove_guide()

        # -- Remove the joints (re-parenting any children)
        new_parent = mref.get(self.input("Root Joint").get()).parent()
        aniseed_toolkit.scene.joints.reparent_unknown_children(self.all_joints(), new_parent)

        # -- Now delete our joint chain
        mref.delete(self.input("Root Joint").get())

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
        if not root_joint or not mref.objExists(root_joint):
            menu["Create Joints"] = self.user_func_create_skeleton
            return menu

        # -- To reach here we definitely have joints, so then we need to check
        # -- whether there is a guide in the scene or not. If there is a guide
        # -- we give the ability to remove it, otherwise we give the ability
        # -- to create it.
        if self.has_guide():
            menu["Remove Guide"] = self.user_func_remove_guide
        else:
            menu["Create Guide"] = self.user_func_create_guide

        return menu

    def user_func_create_skeleton(self, joint_count=None, parent=None):
        """
        This function will build the joint chain for the user.
        """
        # -- Resolve the parent from the argument or the selection
        if not parent:
            selection = mref.selected()
            parent = selection[0] if selection else None

        # -- If we're not given a joint count then we need to
        # -- prompt for one
        if not joint_count:
            requested_count = qtility.request.text(
                title="Joint Count",
                message="How many joints do you want?"
            )

            if not requested_count:
                return

            try:
                joint_count = int(requested_count)
            except ValueError:
                log.warning(f"'{requested_count}' is not a whole number of joints")
                return

        if joint_count < 2:
            return

        # -- Resolve the translation increments for the joints based
        # -- on the expected guide data
        guide_height = self.guide_data()["control_transforms"][-1][-3]
        increment = guide_height / (joint_count - 1)

        # -- Now we cycle the joint count, creating each joint
        # -- in turn
        joints = []
        running_parent = None
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
            mref.get(joint).translateY.set(increment * (min(idx, 1)))

            # -- Store the joint and make this joint the parent
            # -- for the next joint to be made
            joints.append(joint)
            running_parent = joint

        # -- Parent the joint chain under the parent node
        if parent:
            mref.get(joints[0]).set_parent(parent)

        # -- Set our inputs
        self.input("Root Joint").set(joints[0])
        self.input("Tip Joint").set(joints[-1])

        # -- As this component is always expected to be manipulated
        # -- via a guide, lets create the guide now
        guides = self.user_func_create_guide()

        # -- Match the translation of the guide to the parent, this just
        # -- makes the riggers life a little easier as the component will
        # -- show in a contextually relevant location. Note that if there is
        # -- no parent, xform queries the selection instead (which is the
        # -- first guide), leaving the guide where it is.
        mref.xform(
            guides[0],
            translation=mref.xform(
                parent,
                query=True,
                translation=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

    def is_valid(self) -> bool:
        """
        In this function we test the state of the component before we build
        """
        # -- To be valid we expect the root and tip to be
        # -- provided
        root_joint = self.input("Root Joint").get()
        tip_joint = self.input("Tip Joint").get()

        if not root_joint or not mref.objExists(root_joint):
            log.warning("No root joint specified")
            return False

        if not tip_joint or not mref.objExists(tip_joint):
            log.warning("No tip joint specified")
            return False

        return True

    def run(self):
        """
        This is where we build the actual rig
        """
        # -- Get our inputs
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        orient_to_world = self.option("Orient Controls To World").get()

        # -- Read the joints between
        joints = self.all_joints()

        # -- Create a basic transform node to act as the parent
        # -- of everything
        org = aniseed_toolkit.scene.transforms.create(
            classification="org",
            description=descriptive,
            location=location,
            config=self.config,
            parent=self.input("Parent").get(),
            match_to=self.input("Parent").get(),
        )

        # -- Construct the spline setup. This returns a special spline
        # -- class we can use to get access to all the different objects.
        spline_setup = self._create_spline_setup(joints, parent=org, constrain=False)

        # -- Build the main master control
        spine_master_transform = self.input("Spine Master Transform").get()
        master_control = aniseed_toolkit.rig.control.create(
            description=f"{descriptive}Master",
            location=location,
            parent=org,
            shape="core_rounded_square",
            shape_scale=self.control_scale * 1.25,
            config=self.config,
            match_to=spine_master_transform or spline_setup.out_controls[0].full_name(),
        )

        # -- If we need to orient it to the world then we do so by
        # -- adjusting the rotation of the org node
        if orient_to_world:
            mref.get(master_control.org).set_rotation([0, 0, 0], space="world")

        # -- Add the FK and Ik Visibility Attributes
        master_control_node = mref.get(master_control.ctl)
        ik_visibility = master_control_node.add_attribute(
            "ik_visibility",
            attribute_type="bool",
            value=True,
            keyable=False,
        )
        ik_visibility.set(channelBox=True)

        fk_visibility = master_control_node.add_attribute(
            "fk_visibility",
            attribute_type="bool",
            value=False,
            keyable=False,
        )
        fk_visibility.set(channelBox=True)

        # -- Create the IK controls
        ik_controls = self.setup_ik_controls(
            master_control,
            spline_setup,
            spline_setup.out_no_xform_org,
        )

        # -- Now create the Fk control setup
        fk_controls = self.create_fk(spline_setup)

        # -- Constrain the joints to the Fk controls. This is because the fk
        # -- setup is designed to follow the ik setup all the time.
        fk_tweaks = []
        for idx, fk_control in enumerate(fk_controls):

            fk_control = mref.get(fk_control.ctl)
            joint = mref.get(joints[idx])

            # -- Create the tweaker
            offset_control = aniseed_toolkit.rig.control.create(
                description=f"{descriptive}FkOffset",
                location=location,
                parent=fk_control.full_name(),
                shape="core_circle",
                shape_scale=self.control_scale,
                config=self.config,
                match_to=fk_control.full_name(),
            )
            fk_tweak = mref.get(offset_control.ctl)
            fk_tweaks.append(fk_tweak)

            # -- If requested, the first fk control is turned into a
            # -- mechanical node which the animator cannot interact with
            if self.option("Invalidate First Fk Control").get() and not idx:
                fk_control.rename(
                    self.config.generate_name(
                        classification="amech",
                        description=self.config.extract_description(fk_control.name()),
                        location=self.config.extract_location(fk_control.full_name()),
                        counter=self.config.extract_counter(fk_control.full_name()),
                    ),
                )
                fk_control.lock_transform_attributes(hide=True)
                for shape in fk_control.shapes():
                    mref.delete(shape)

            # -- The offset control is visible when both the fk visibility
            # -- and the controls own show_offset attribute are on.
            show_offset_attribute = fk_control.add_attribute(
                "show_offset",
                attribute_type="bool",
                keyable=True,
                value=False if idx else self.option("Show First Fk Offset Control").get(),
            )
            show_offset_multiplier = mref.create("floatMath")
            show_offset_multiplier.operation.set(2)  # -- Multiply
            fk_visibility.connect(show_offset_multiplier.floatA)
            show_offset_attribute.connect(show_offset_multiplier.floatB)

            if self.option("Align Offsets To Bone").get():
                mref.get(offset_control.org).match_to(joint)

            aniseed_toolkit.scene.constraints.parent_and_scale(fk_tweak, joint)

            # -- Hook up the visibility
            for nurbs_shape in fk_control.shapes():
                fk_visibility.connect(nurbs_shape.attr("visibility"))

            for nurbs_shape in fk_tweak.shapes():
                show_offset_multiplier.outFloat.connect(nurbs_shape.attr("visibility"))

        # -- Hook the ik visibility up to the ik control shapes. Note that the
        # -- tweaker shape visibilities are already driven by their show_tweak
        # -- attribute, so for those this connection fails (silently, by
        # -- design of connect) and the show_tweak connection is kept.
        for ik_control in ik_controls:
            for nurbs_shape in mref.get(ik_control.ctl).shapes():
                ik_visibility.connect(nurbs_shape.attr("visibility"))

        # -- Finally we set our output variables
        self.output("Root Transform").set(spline_setup.out_trace_joints[0].name())
        self.output("Tip Transform").set(spline_setup.out_trace_joints[-1].name())
        self.output("Master Control").set(master_control.ctl)
        self.output("Fk Root").set(fk_tweaks[0].name())
        self.output("Fk Tip").set(fk_tweaks[-1].name())

    def setup_ik_controls(self, master_control, spline_setup, no_transform_node):
        """
        This will construct the IK controls for the rig. The no transform
        node is not used here, but is required by the Tri variant.
        """
        # -- Read out the option data we will need
        number_of_controls = self.option("Number Of Controls").get()
        descriptive = self.option("Descriptive Prefix").get()

        # -- Define our running parent
        parent = master_control.ctl

        tweaker_vis_attribute = self._add_tweaker_visibility_attribute(master_control)

        # -- We need to keep track of the ik controls we build
        ik_controls = []

        for idx in range(number_of_controls):

            # -- Construct a control and a tweaker. The tweaker is just
            # -- a child control - but it never acts as a parent. Its a nice
            # -- way to allow an animator to be able to adjust a single control
            # -- without affecting any of its children.
            base_control, base_control_tweaker = self._create_spline_point_control(
                description=descriptive,
                parent=parent,
                shape_scale=self.control_scale,
                spline_point=spline_setup.out_controls[idx],
            )

            # -- Note: The tweaker shape visibilities are already driven by
            # -- the show_tweak attribute, so this connection fails (silently,
            # -- by design of connect) and the show_tweak connection is kept.
            for shape in mref.get(base_control_tweaker.ctl).shapes():
                tweaker_vis_attribute.connect(shape.attr("visibility"))

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

    def create_fk(self, spline_setup):
        """
        Creates our FK controllers
        """
        # -- Read out our option data
        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- We want our hierarchy to be fk - so we need to track the
        # -- parent on each iteration
        next_parent = spline_setup.out_org.full_name()

        # -- This is where we will store the output
        fk_controls = []

        for idx, trace_joint in enumerate(spline_setup.out_anchor_points):

            # -- Create the actual control hierarchy
            fk_control = aniseed_toolkit.rig.control.create(
                description=f"{descriptive}Fk",
                location=location,
                parent=next_parent,
                shape=self.option("Shape").get(),
                shape_scale=self.control_scale,
                config=self.config,
                match_to=trace_joint.full_name(),
            )

            # -- We need the automated FK setup in the spline rig to
            # -- drive our FK controls. This is because the FK controls
            # -- in the spline rig auto-follow the IK.
            aniseed_toolkit.scene.transforms.drive_from_local_matrix(trace_joint, fk_control.org)

            if self.option("Orient FK Controls To World").get():
                mref.get(fk_control.zero).set_rotation([0, 0, 0], space="world")

            # -- Set the corresponding output plug
            self.output(f"FK Control {idx}").set(fk_control.ctl)

            # -- Store the fk control
            fk_controls.append(fk_control)

            # -- The next fk control is parented under a realigner, which
            # -- is a child of this fk control matched to the trace joint.
            realigner = mref.get(
                aniseed_toolkit.scene.transforms.create(
                    classification="mech",
                    description=f"{descriptive}FkReAlign",
                    location=location,
                    parent=fk_control.ctl,
                    config=self.config,
                ),
            )
            realigner.match_to(trace_joint)

            next_parent = realigner.name()

        return fk_controls

    def create_doubled_control(self, descriptive, location, parent, shape_scale, match_to, orient_to_world, drive_this):
        """
        This is a convenience function for creating two controls that sit atop of
        each other. This is useful for creating hierarchies of controls where
        each control has a sub control which can be manipulated in isolation.
        """
        main_control = aniseed_toolkit.rig.control.create(
            description=descriptive,
            location=location,
            parent=parent,
            shape="core_pinched_circle",
            shape_scale=shape_scale,
            config=self.config,
            match_to=match_to,
        )
        tweak_control = aniseed_toolkit.rig.control.create(
            description=f"{descriptive}Tweak",
            location=location,
            parent=main_control.ctl,
            shape="core_circle",
            shape_scale=shape_scale * 0.75,
            config=self.config,
            match_to=match_to,
        )
        if orient_to_world:
            mref.get(main_control.org).set_rotation([0, 0, 0], space="world")

        # -- The item we're given to drive is constrained to the tweaker
        mref.parentConstraint(
            tweak_control.ctl,
            drive_this,
            maintainOffset=True,
        )

        # -- Add the tweak attribute
        show_tweak = mref.get(main_control.ctl).add_attribute(
            "show_tweak",
            attribute_type="bool",
            keyable=False,
            value=self.option("Default Ik Tweak Visibility").get(),
        )
        show_tweak.set(channelBox=True)

        for shape in mref.get(tweak_control.ctl).shapes():
            show_tweak.connect(shape.attr("visibility"), force=True)

        # -- As we're made up of a pair of controls, we return
        # -- a list of them both.
        return [
            main_control,
            tweak_control,
        ]

    def _create_spline_point_control(self, description, parent, shape_scale, spline_point):
        """
        Creates a doubled control which is matched to (and drives) the
        given spline point.
        """
        return self.create_doubled_control(
            descriptive=description,
            location=self.option("Location").get(),
            parent=parent,
            shape_scale=shape_scale,
            match_to=spline_point.full_name(),
            orient_to_world=self.option("Orient Controls To World").get(),
            drive_this=spline_point.full_name(),
        )

    def _add_tweaker_visibility_attribute(self, master_control):
        """
        Adds the (non keyable, channel box visible) tweaker_visibility
        attribute to the master control and returns it.
        """
        tweaker_vis_attribute = mref.get(master_control.ctl).add_attribute(
            "tweaker_visibility",
            value=False,
            attribute_type="bool",
            keyable=False,
        )
        tweaker_vis_attribute.set(channelBox=True)
        return tweaker_vis_attribute

    def user_func_create_guide(self):
        """
        This function will create the guide setup
        """
        # -- Check if the guide already exists first
        if self.has_guide():
            return []

        # -- Read the joint chain
        joints = self.all_joints()

        # -- Create the spline setup - note that this same function is called
        # -- when building the rig too. This ensures the behaviour of the guide
        # -- and the rig are the same
        spline_setup = self._create_spline_setup(joints=joints)

        # -- Create a node to parent everything under. Note that this uses
        # -- maya's naming (via the createNode passthrough) as mref.create
        # -- would uniquify the name differently.
        guide_org = mref.createNode(
            "transform",
            name="splineGuide",
        )
        spline_setup.out_org.set_parent(guide_org)

        # -- We now need to build actual guide objects to drive our
        # -- spline spine. These guides will be FK
        guides = self.create_guide_controls(guide_org.name(), spline_setup)

        for guide in guides:
            aniseed_toolkit.run("Tag Node", guide, "ControlGuide")

        # -- Now that we have built the guide we need to store
        # -- the reference to the guide node in the guide data.
        guide_data = self.guide_data()
        guide_data["LinkedGuide"] = guide_org.name()
        self.option("GuideData").set(guide_data)

        # -- If there is a parent of the root then we constrain our
        # -- setup to that
        root_parent = mref.get(joints[0]).parent()
        if root_parent:
            mref.parentConstraint(
                root_parent,
                guide_org,
                maintainOffset=True,
            )

        mref.select(guides[0])
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
            parent = guides[-1]
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
        aniseed_toolkit.scene.joints.unreference(joints)

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
        guide_controls = aniseed_toolkit.rig.tagging.all_children(guide_root, "ControlGuide")

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
        with aniseed_toolkit.scene.joints.HeldTransforms(joints):
            mref.delete(str(guide_data["LinkedGuide"]))

        # -- Finally we remove the entry for the linked guide (marking this
        # -- as not having an active guide) and we store the updated guide
        # -- information.
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

        # -- Build the spline setup. This returns a SplineSetup class which
        # -- gives us access to all the items it has built for us. We need to
        # -- give the spline builder the general parent transform for all the
        # -- local matrices - so for us, this is our root joint transform
        spline_setup = aniseed_toolkit.run(
            "Create Spline Setup",
            parent=parent,
            joints=joints,
            org_transform=mref.get(self.input("Root Joint").get()).get_matrix(space="world"),
            control_transforms=self.guide_data()["control_transforms"],
            constrain=constrain,
            lock_end_orientations=self.option("Lock End Orientations To Controls").get(),
        )

        # -- Now we just need to name all the items in the spline setup
        # -- based upon our rigging config.
        naming = [
            ([spline_setup.out_org], "org", "SplineSolve"),
            (spline_setup.out_controls, "loc", "PointTransform"),
            (spline_setup.out_upvectors, "loc", "UpvectorTransform"),
            (spline_setup.out_clusters, "cls", "ClusterTransform"),
            (spline_setup.out_trace_joints, "jnt", "Tracer"),
            (spline_setup.out_anchor_points, "jnt", "Anchor"),
            ([spline_setup.out_no_xform_org], "org", "NoTransform"),
        ]
        for nodes, classification, description in naming:
            for node in nodes:
                node.rename(
                    self.config.generate_name(
                        classification=classification,
                        description=f"{descriptive}{description}",
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
        """
        Returns all the joints between the root and the tip joint
        """
        return aniseed_toolkit.scene.joints.get_between(
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
        )

    def has_guide(self):
        """
        Checks whether this has a valid guide or not
        """
        guide = self.guide_data().get("LinkedGuide")
        return bool(guide and mref.objExists(guide))

    def update_outputs(self) -> None:
        """
        This function is called whenever the start or end joint is changed. We
        use this to count the amount of joints which will be created and ensure
        that each one is represented by an output pin.
        This ensures we are supporting a dynamic number of output attributes based
        on the inputs.
        """
        aniseed_toolkit.rig.component_outputs.declare_joint_outputs(
            self,
            "FK Control",
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
        )

    def _mirror_joints(self) -> list:
        """
        Returns all the joints between the root and the tip, or an empty
        list if either is missing or the tip is not below the root.
        """
        root_joint = self.input("Root Joint").get()
        tip_joint = self.input("Tip Joint").get()

        if not root_joint or not tip_joint:
            return []

        if not mref.objExists(root_joint) or not mref.objExists(tip_joint):
            return []

        try:
            return self.all_joints()
        except ValueError:
            return []

    def _mirror_guides(self) -> list:
        """
        Returns the control guides (sorted, as user_func_remove_guide reads
        them) if there is an active guide, otherwise an empty list.
        """
        if not self.has_guide():
            return []

        return sorted(
            aniseed_toolkit.rig.tagging.all_children(
                self.guide_data()["LinkedGuide"],
                "ControlGuide",
            )
        )

    def _mirror_control_matrices(self) -> list:
        """
        Returns the world matrix of each spline control point: from the
        guides if there is an active guide, otherwise from the stored guide
        data (which is relative to the root joint).
        """
        guides = self._mirror_guides()
        if guides:
            return [
                mref.xform(guide, query=True, matrix=True, worldSpace=True)
                for guide in guides
            ]

        root_matrix = om.MMatrix(
            mref.xform(self.input("Root Joint").get(), query=True, matrix=True, worldSpace=True),
        )
        relative_matrices = (
            self.guide_data().get("control_transforms")
            or self.default_guide_data()["control_transforms"]
        )

        matrices = []
        for relative_matrix in relative_matrices:
            world_matrix = om.MMatrix(relative_matrix) * root_matrix
            matrices.append(
                [world_matrix.getElement(row, column) for row in range(4) for column in range(4)],
            )
        return matrices

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the joints from the root to the tip, followed by the control
        guides if there is an active guide. The joints come first because a
        mirrored component always has a guide after entering the stack, even when the
        original does not.
        """
        return self._mirror_joints() + self._mirror_guides()

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the root joint, which is where the mirrored component creates
        its joints.
        """
        root_joint = self.input("Root Joint").get()
        if not root_joint or not mref.objExists(root_joint):
            return ""

        parent = mref.get(root_joint).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        The copied guide data still links to the original's guide, which would
        stop this component creating its own, so that link is removed. If the
        other side joints already exist this component uses them, otherwise it
        creates a chain of the same length as the original's.
        """
        guide_data = copy.deepcopy(self.guide_data())
        guide_data["LinkedGuide"] = ""
        self.option("GuideData").set(guide_data)

        original_joints = mirrored_from._mirror_joints()

        if self.mirror_mixin_counterparts_exist(original_joints, self._mirror_joints()):
            self.option("Joint Count").set(0)
            return

        self.option("Joint Count").set(len(original_joints) if len(original_joints) >= 2 else 0)

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        While this component's guide is active its joints follow the guide, with
        offsets taken from where the joints were when the guide was made, so
        they do not take the mirrored transforms exactly. The guide is
        therefore removed, the joints mirrored directly and the guide data
        set to the mirror of the original's control points. The guide is then
        made again (with the joints in place) if the original has one.
        """
        original_joints = mirrored_from._mirror_joints()
        mirrored_joints = self._mirror_joints()

        if not original_joints or len(original_joints) != len(mirrored_joints):
            return

        original_matrices = mirrored_from._mirror_control_matrices()

        self.user_func_remove_guide()

        aniseed_toolkit.scene.mirror.mirror_transforms(
            transforms=original_joints,
            targets=mirrored_joints,
            across=self.MIRROR_PLANE,
            behaviour=True,
        )

        # -- Mirror each control point, then store it relative to this component's
        # -- root joint. The spline's upvectors are offset along each control
        # -- point's X axis. A behaviour mirror negates that axis, which would
        # -- put this component's upvectors on the other side of its curve and twist
        # -- it slightly differently from the original as it bends. So after the
        # -- behaviour mirror each control point is turned 180 degrees about
        # -- its Z axis, which mirrors its X (and Y) axis instead.
        root_joint = self.input("Root Joint").get()
        buffer = mref.create("transform")
        control_transforms = []

        for matrix in original_matrices:
            mref.xform(buffer.full_name(), matrix=matrix, worldSpace=True)
            aniseed_toolkit.scene.mirror.mirror_transforms(
                transforms=[buffer.full_name()],
                across=self.MIRROR_PLANE,
                behaviour=True,
            )

            mirrored_matrix = mref.xform(buffer.full_name(), query=True, matrix=True, worldSpace=True)
            for index in range(8):
                if index % 4 != 3:
                    mirrored_matrix[index] *= -1
            mref.xform(buffer.full_name(), matrix=mirrored_matrix, worldSpace=True)

            control_transforms.append(
                aniseed_toolkit.scene.transforms.get_relative_matrix(buffer.full_name(), root_joint),
            )

        buffer.delete()

        guide_data = self.guide_data()
        guide_data["control_transforms"] = control_transforms
        guide_data["LinkedGuide"] = ""
        self.option("GuideData").set(guide_data)

        if mirrored_from.has_guide():
            self.user_func_create_guide()


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
        """
        Locks the component to four controls, hiding the Number Of Controls
        and FK Interaction Mode options.
        """
        super().__init__(*args, **kwargs)

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

        # -- We need to return the list of controls we create, so we
        # -- define a variable for that
        ik_controls = []

        # -- Create the hip, lower mid, chest and upper mid controls
        # -- in that order.
        control_definitions = [
            (f"{descriptive}Hip", master_control.ctl, 1.1, 0),
            (descriptive, None, 1.0, 1),
            (f"{descriptive}Chest", master_control.ctl, 1.0, 3),
            (descriptive, None, 1.0, 2),
        ]
        for description, parent, scale, point_index in control_definitions:

            # -- The mid controls are children of the control before them
            parent = parent or ik_controls[-2].ctl

            ik_controls.extend(
                self._create_spline_point_control(
                    description=description,
                    parent=parent,
                    shape_scale=self.control_scale * scale,
                    spline_point=spline_setup.out_controls[point_index],
                ),
            )

        # -- Now our controls are created we can set our outputs. These
        # -- are the hip tweaker and the chest tweaker.
        self.output("Root Control").set(ik_controls[1].ctl)
        self.output("Tip Control").set(ik_controls[5].ctl)

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
        """
        Adds the Ribbon Cross Vector option and locks the component to five
        (hidden) controls - three primary and two bezier style.
        """
        super().__init__(*args, **kwargs)

        # -- This component as a new option to define the cross vector
        # -- of the ribbon (that is the direction the width should be in).
        self.declare_option(
            name="Ribbon Cross Vector",
            value=[1, 0, 0],
        )

        # -- Force this component to use five controls (three primary and
        # -- two bezier style) and do not expose it to the user
        self.option("Number Of Controls").set(5)
        self.option("Number Of Controls").set_hidden(True)

    def option_widget(self, option_name: str):
        """
        Return a specific widget for the vector option.
        """
        if option_name == "Ribbon Cross Vector":
            return aniseed.widgets.VectorWidget()
        return super().option_widget(option_name)

    def user_func_create_guide(self):
        """
        We want a more bespoke guide hierarchy for our tri component
        """
        # -- Check if the guide already exists first (the base class would
        # -- return no guides, which we cannot re-parent)
        if self.has_guide():
            return []

        guides = super().user_func_create_guide()
        mref.get(guides[2]).set_parent(guides[0])
        mref.get(guides[-1]).set_parent(guides[0])
        return guides

    def setup_ik_controls(self, master_control, spline_setup, no_transform_node):
        """
        This is where the main difference is between the tri component and the
        standard component.
        """
        # -- Read our options and inputs.
        descriptive = self.option("Descriptive Prefix").get()
        control_scale = float(self.control_scale)

        tweaker_vis_attribute = self._add_tweaker_visibility_attribute(master_control)

        # -- Now we can start building our actual controls.
        hip_control, hip_control_tweaker = self._create_spline_point_control(
            description=f"{descriptive}Hip",
            parent=master_control.ctl,
            shape_scale=control_scale * 1.1,
            spline_point=spline_setup.out_controls[0],
        )

        mid_control, mid_control_tweaker = self._create_spline_point_control(
            description=f"{descriptive}Mid",
            parent=master_control.ctl,
            shape_scale=control_scale * 0.9,
            spline_point=spline_setup.out_controls[2],
        )
        show_mid_point_controls = mref.get(mid_control.ctl).add_attribute(
            "ShowMidPointControls",
            value=None,
            attribute_type="bool",
            defaultValue=False,
            keyable=True,
        )

        upper_mid_control, upper_mid_control_tweaker = self._create_spline_point_control(
            description=f"{descriptive}UpperMid",
            parent=mid_control_tweaker.ctl,
            shape_scale=control_scale * 0.9,
            spline_point=spline_setup.out_controls[3],
        )
        show_mid_point_controls.connect(mref.get(upper_mid_control.org).attr("visibility"))

        lower_mid_control, lower_mid_control_tweaker = self._create_spline_point_control(
            description=f"{descriptive}LowerMid",
            parent=mid_control_tweaker.ctl,
            shape_scale=control_scale * 0.9,
            spline_point=spline_setup.out_controls[1],
        )
        show_mid_point_controls.connect(mref.get(lower_mid_control.org).attr("visibility"))

        chest_control, chest_control_tweaker = self._create_spline_point_control(
            description=f"{descriptive}Chest",
            parent=master_control.ctl,
            shape_scale=control_scale * 1.1,
            spline_point=spline_setup.out_controls[4],
        )

        # -- Unlike the base component, the tweaker visibility attribute is
        # -- forced in, replacing the show_tweak connections.
        tweakers = [
            hip_control_tweaker,
            chest_control_tweaker,
            mid_control_tweaker,
            lower_mid_control_tweaker,
            upper_mid_control_tweaker,
        ]
        for tweaker in tweakers:
            for shape in mref.get(tweaker.ctl).shapes():
                tweaker_vis_attribute.connect(shape.attr("visibility"), force=True)

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
        self.output("Root Control").set(hip_control_tweaker.ctl)
        self.output("Tip Control").set(chest_control_tweaker.ctl)
        return [
            hip_control,
            hip_control_tweaker,
            mid_control,
            mid_control_tweaker,
            upper_mid_control,
            upper_mid_control_tweaker,
            lower_mid_control,
            lower_mid_control_tweaker,
            chest_control,
            chest_control_tweaker,
        ]

    def setup_auto_ribbon(self, bottom_control, mid_control, top_control, no_transform_node):
        """
        This will generate a ribbon mesh and have the mid control follow that
        newly created mesh.
        """
        location = self.option("Location").get()

        # -- We need to start by creating a specific set of joints which we will
        # -- skin our ribbon to.
        top_joint = mref.create("joint", parent=top_control)
        top_joint.rename(
            self.config.generate_name(
                classification=self.config.mechanical,
                description="AutoRibbonTop",
                location=location,
            )
        )
        top_joint.match_to(top_control)

        # -- Now create the second joint. At this point we have a joint to
        # -- follow the top control and a joint to follow the bottom control.
        bottom_joint = mref.create("joint", parent=bottom_control)
        bottom_joint.rename(
            self.config.generate_name(
                classification=self.config.mechanical,
                description="AutoRibbonBottom",
                location=location,
            )
        )
        bottom_joint.match_to(bottom_control)

        # -- Now we can build the actual geometry. As we will skin this mesh it
        # -- is important that it does not get transformed - so we place it under the
        # -- no transform node.
        mesh = self.generate_ribbon_mesh(bottom_control, mid_control, top_control)
        mesh.set_parent(no_transform_node)

        # -- Skin the mesh to the two joints we created.
        skin = mref.skinCluster(
            [
                top_joint.full_name(),
                bottom_joint.full_name(),
                mesh.full_name(),
            ],
            bindMethod=0,
            skinMethod=0,
            ignoreHierarchy=True,
        )[0]

        # -- Now we need to be specific about the weighting. We want the
        # -- weighting of the end-point verticed to be 100% to their respective
        # -- bones, but the mid point vertices to be 50/50 between the two.
        weights = [
            ("vtx[0:1]", [(bottom_joint.full_name(), 1.0)]),
            ("vtx[2:5]", [(bottom_joint.full_name(), 0.5), (top_joint.full_name(), 0.5)]),
            ("vtx[6:7]", [(top_joint.full_name(), 1.0)]),
        ]
        for vertices, transform_values in weights:
            mref.skinPercent(skin, f"{mesh.full_name()}.{vertices}", transformValue=transform_values)

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

        Width is measured across each transform's cross vector axis.

        Returns:
            The mesh transform
        """
        name = self.config.generate_name(
            classification=self.config.mechanical,
            description=name,
            location=self.option("Location").get(),
        )

        # -- Read our option data
        cross_vector = self.option("Ribbon Cross Vector").get()

        # -- Determine the half width of the mesh
        half_width = width * 0.5

        # -- We will use the constructed points to build
        # -- the faces, so track them here
        points = []

        for transform in [top, middle, bottom]:

            # -- Get the world matrix of the object
            m = om.MMatrix(mref.get(transform).get_matrix(space="world"))
            tm = om.MTransformationMatrix(m)

            # -- Extract the world position
            pos = tm.translation(om.MSpace.kWorld)

            # -- Get the cross axis
            axis = om.MVector(*cross_vector) * m
            axis.normalize()

            # -- Calculate and store the left and right position
            points.append(pos - (axis * half_width))
            points.append(pos + (axis * half_width))

        # -- Now we construct the vertex array
        verts = [(p.x, p.y, p.z) for p in points]

        # -- And finally construct the face array
        faces = [
            [0, 1, 3, 2],  # bottom quad
            [2, 3, 5, 4],  # top quad
        ]

        # -- With all this information we can construct our two
        # -- polygons.
        mesh = mref.polyCreateFacet(point=[verts[i] for i in faces[0]], name=name)[0]
        mref.polyAppendVertex(mesh, append=[verts[i] for i in faces[1]])

        return mesh

    def constrain_to_midpoint_vertex(self, mesh, transform):
        """
        Here we need to make the given transform follow the vertices in the middle
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

        # -- Set up the geometry contraint, pinning it to the middle of the
        # -- far edge of the ribbon
        constraint = mref.pointOnPolyConstraint(mesh, buffer, maintainOffset=False)[0]
        constraint.attr(f"{mesh.name()}U0").set(1)
        constraint.attr(f"{mesh.name()}V0").set(0.5)

        # -- Finally we need the transform node to now be a child
        # -- of our created buffer.
        transform.set_parent(buffer)
        return constraint

    def create_guide_controls(self, guide_org, spline_setup):
        """
        We want our guides to be in a flat hierarchy
        """
        # -- Cycle the transformable nodes and create a guide
        # -- for each one
        guides = [
            aniseed_toolkit.run(
                "Create Guide",
                joint=control_transform.name(),
                parent=guide_org,
            )
            for control_transform in spline_setup.out_controls
        ]

        # -- Set the parenting for the guides
        mref.get(guides[1]).set_parent(guides[2])
        mref.get(guides[3]).set_parent(guides[2])
        return guides
