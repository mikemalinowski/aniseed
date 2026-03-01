# NOT PRODUCTION READY!
import aniseed
import qtility
import aniseed_toolkit
import functools
import maya.cmds as mc
from Qt import QtWidgets

# -- This tentacle component uses the Blur Studios twist spline setup
# -- which can be found here: https://github.com/blurstudio/TwistSpline
# -- We do not distribute that directly within Aniseed, therefore we only
# -- make this component available if the user/developer/rigger has
# -- downloaded and made that module available.
optional_rig_component = object
try:
    import twistSplineBuilder
    optional_rig_component = aniseed.RigComponent
except ImportError:
    pass


# ------------------------------------------------------------------------------
class TentacleComponent(aniseed.RigComponent):

    identifier = 'Limb : Tentacle'
    version = 1

    def __init__(self, *args, **kwargs):
        super(TentacleComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The control parent for the tentacle controls",
            group="Control Rig",
        )

        self.declare_input(
            name="Start Joint",
            description="The first joint in the tentacle chain",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_input(
            name="End Joint",
            description="The last joint in the tentacle chain",
            validate=False,
            group="Optional Twist Joints",
        )

        self.declare_option(
            name="Descriptive Prefix",
            value="Tentacle",
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
            name="Control Count",
            value=4,
            group="Behaviour",
        )

        self.declare_option(
            name="GuideData",
            value=dict(),
            hidden=True,
        )

        # -- This component has a dynamic amount of resolved joints. Therefore
        # -- we want to ensure each joint is represented with an output attribute.
        # -- In order to do that we rebuild the output attributes whenever a
        # -- situation occurs which alters the joint count.
        self.input("Start Joint").value_changed.connect(self.update_outputs)
        self.input("End Joint").value_changed.connect(self.update_outputs)


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
            if output_plug.name().startswith("Out Joint"):
                self.remove_output(output_plug.name())

        # -- Attempt to get the joints. Note that this is wrapped in an exception
        # -- statement, as its possible one or more of these attributes are blank.
        try:
            joints = aniseed_toolkit.run(
                "Get Joints Between",
                self.input("Start Joint").get(),
                self.input("End Joint").get(),
            )
        except:
            joints = []

        # -- We now cycle the joints and declare a new output attribute
        # -- to represent it
        for idx, joint in enumerate(joints):
            self.declare_output(name="Out Joint %s" % idx)

    def input_widget(self, requirement_name) -> QtWidgets.QWidget:
        """
        This function allows us to return custom QWidgets to represent
        various inputs
        """
        if requirement_name in ["Parent", "Start Joint", "End Joint"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str) -> QtWidgets.QWidget:
        """
        This function allows us to return custom QWidgets to represent
        various options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    def is_valid(self) -> bool:
        """
        We only consider this to be valid if we have guide data and there is
        not a live guide currently attached.
        """
        guide_data = self.option("GuideData").get()

        if not guide_data:
            return False

        guide_org = guide_data.get("LinkedGuide")

        if guide_org and mc.objExists(guide_org):
            print("You must remove the guide before building")
            return False

        return True

    def user_functions(self) -> dict:
        """
        We expose functionality for creating joints as well as building and
        removing the guide. We also expose functionality to change the joint
        count.
        """
        menu = super(TentacleComponent, self).user_functions()

        # -- Only show the skeleton creation tools if we dont have a skeleton
        leg_joint = self.input("Start Joint").get()

        # -- If we dont have any joints we dont want to show any tools
        # -- other than the joint creation tool
        if not leg_joint or not mc.objExists(leg_joint):
            menu["Create Joints"] = functools.partial(self.user_func_create_skeleton)
            return menu

        guide_data = self.option("GuideData").get()
        linked_guide = guide_data.get("LinkedGuide")

        # -- Depending on whether we have a guide or not, change what we show
        # -- in the actions menu
        if linked_guide and mc.objExists(linked_guide):
            menu["Remove Guide"] = functools.partial(self.user_func_remove_guide)
        else:
            menu["Create Guide"] = functools.partial(self.user_func_build_guide)

        # -- Add in the function which allows us to change
        # -- the joint count
        menu["Change Joint Count"] = functools.partial(self.user_func_change_joint_count)
        return menu

    def user_func_create_skeleton(self, joint_count: int = None, parent: str = None) -> list:
        """
        This will generate the joint hierarchy for the user based on the given
        joint count. If no joint count is given a ui prompt will be raised.

        Args:
            joint_count: The number of joints which should be created
            parent: The name of the node the joint should be a child of. If omitted
                then the current selection will be used.
        """
        # -- If we dont have a parent then attempt to resolve
        # -- it from the active selection
        try:
            parent = parent or mc.ls(sl=True)[0]
        except IndexError:
            parent = None

        # -- If we're not given a joint count then we prompt the user
        # -- to give one
        joint_count = joint_count or int(
            qtility.request.text(
                title="Joint Count",
                message="How many joints do you want?"
            ),
        )

        # -- Validate the number the user gave
        if not joint_count or joint_count < 2:
            return

        # -- We want to keep track of the joints we create so that
        # -- we can return them
        joints = []

        # -- We always create our joints along X between zero and ten, so we
        # -- calculate the increment between each joint for the requested
        # -- joint count.
        increment = 10.0 / float(joint_count)

        # -- Create the joint and ensure its spaced correctly.
        for idx in range(joint_count):
            joint = aniseed_toolkit.run(
                "Create Joint",
                description=self.option("Descriptive Prefix").get(),
                location=self.option("Location").get(),
                parent=parent,
                match_to=parent,
                config=self.config
            )
            if idx != 0:
                mc.setAttr(
                    f"{joint}.translateX",
                    increment,
                )
            joints.append(joint)
            parent = joint

        # -- Set the input attributes to the newly created joints.
        self.input("Start Joint").set(joints[0])
        self.input("End Joint").set(joints[-1])

        # -- We always want the user to interact with this component through
        # -- the guide, so ensure we build the guide as soon as the joints are
        # -- created.
        self.user_func_build_guide()

        return joints

    def user_func_build_guide(self):
        """
        This function will construct a guide rig around the joints
        """
        # -- Get the list of joints between the start and end joint (inclusive)
        joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Start Joint").get(),
            self.input("End Joint").get(),
        )

        # -- Use the builder class to construct the rig. Note that our guide is
        # -- actually the same as the main control rig.
        builder = TentacleBuilder(
            cv_count=self.option("Control Count").get(),
            joint_count=len(joints),
            config=self.config,
            location=self.option("Location").get(),
            description=self.option("Descriptive Prefix").get(),
        )

        # -- Constrain the deformation joints to the mechanical joints
        # -- in the guide rig. Note that we explicity disable the constraints
        # -- rest position property, as we do not want the joints to "ping"
        # -- back when the guide is removed.
        for idx, mech_joint in enumerate(builder.joint_names()):
            cns = mc.parentConstraint(
                mech_joint,
                joints[idx],
                maintainOffset=False,
            )[0]
            mc.setAttr(f"{cns}.enableRestPosition", 0)
            cns = mc.scaleConstraint(
                mech_joint,
                joints[idx],
                maintainOffset=False,
            )[0]
            mc.setAttr(f"{cns}.enableRestPosition", 0)

        # -- Get the guide data, and fill in the linked guide to point
        # -- to our guide node
        guide_data = self.option("GuideData").get()
        guide_xform_data = guide_data.get("AttributeData", dict())
        guide_data["LinkedGuide"] = builder.org

        # -- If there was any previously stored guide data then we read it
        # -- and apply the attribute data
        counter = 1
        for tag, attribute_data in guide_xform_data.items():
            node = aniseed_toolkit.run(
                "Find First Child With Tag",
                builder.org,
                tag,
            )
            if not node:
                break

            guide_xform_data[tag] = dict()
            for attr, value in attribute_data.items():
                mc.setAttr(f"{node}.{attr}", value)
            counter += 1

        # -- Finally serialise the guide data now that we have modified it
        self.option("GuideData").set(guide_data)

    def user_func_change_joint_count(self, joint_count: int = None) -> None:
        """
        This function will rebuild the joint structure to a given joint
        count, managing any child joints that need reparenting as part
        of the process.
        """
        # -- Validate that we're being asked to create a valid
        # -- number of joints
        if not joint_count:
            joint_count = joint_count or int(
                qtility.request.text(
                    title="Joint Count",
                    message="How many joints do you want?"
                ),
            )
        if not joint_count or joint_count < 2:
            return

        # -- Get the current joints
        joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Start Joint").get(),
            self.input("End Joint").get(),
        )

        # -- Determine the main parent - this is the parent of the top
        # -- level joint
        main_parent = mc.listRelatives(joints[0], parent=True)[0]

        # -- Declare a variable where we will store any joints we need to
        # -- reparent. We store the name of the joint as well as the current
        # -- parent name.
        joints_to_reparent = dict()
        # -- Un parent any children, storing the parent name
        for joint in joints:
            for child in mc.listRelatives(joint, children=True, type="joint") or []:
                if child not in joints:
                    joints_to_reparent[child] = joint
                    mc.parent(child, world=True)

        # -- Remove the guide
        self.user_func_remove_guide()

        # -- Now we can delete the existing joints and build the new joints
        mc.delete(joints)
        new_joints = self.user_func_create_skeleton(
            joint_count=joint_count,
            parent=main_parent,
        )

        # -- Now that we have a set of new joints made, we attempt to reparent
        # -- any joints
        for child, parent in joints_to_reparent.items():
            if not parent or not mc.objExists(parent):
                parent = main_parent
            mc.parent(child, parent)

    def run(self) -> bool:
        """
        This function is called when the rig is being built
        """
        # -- Get the list of joints that make up the tentacle chain
        joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Start Joint").get(),
            self.input("End Joint").get(),
        )

        # -- Access the guide data
        guide_data = self.option("GuideData").get()
        guide_xform_data = guide_data.get("AttributeData", dict())

        # -- Access any bone data
        bone_matrices = guide_data.get("BoneMatrices", dict())

        # -- Transform our bones to their expected positions
        for bone_name, matrix in bone_matrices.items():
            if mc.objExists(bone_name):
                mc.xform(bone_name, matrix=matrix)

        # -- Use the tentacle builder to construct the rig
        builder = TentacleBuilder(
            cv_count=self.option("Control Count").get(),
            joint_count=len(joints),
            config=self.config,
            location=self.option("Location").get(),
            description=self.option("Descriptive Prefix").get(),
        )

        # -- We now need to set various attributes on the rig to match the guide
        counter = 1
        for tag, attribute_data in guide_xform_data.items():
            node = aniseed_toolkit.run(
                "Find First Child With Tag",
                builder.org,
                tag,
            )
            if not node:
                break

            for attr, value in attribute_data.items():
                mc.setAttr(f"{node}.{attr}", value)
            counter += 1

        # -- TODO: We should zero the controls at this stage!
        pass

        # -- Now we need to make the controls location be the zero point.
        # -- We do this by taking the control and getting the mech parent
        # -- and matching the transform of hte mech parent to the control
        # -- then zero the control
        for control in builder.controls():

            if "Twist" in control:
                continue

            control = aniseed_toolkit.run("Get Control", control)
            mech_parent = mc.listRelatives(control.org, p=True)[0]

            mc.xform(
                mech_parent,
                matrix=mc.xform(
                    control.ctl,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )
            aniseed_toolkit.run("Zero Control", control.ctl)

        # -- We now constrain our deformation joints to the control rig
        for idx, mech_joint in enumerate(builder.joint_names()):
            cns = mc.parentConstraint(
                mech_joint,
                joints[idx],
                maintainOffset=True,
            )[0]
            cns = mc.scaleConstraint(
                mech_joint,
                joints[idx],
                maintainOffset=True,
            )[0]

            # -- Set the corresponding output plug
            tag = "Out Joint %s" % idx
            self.output(tag).set(mech_joint)

        # -- If we were given a parent then we parent our entire setup
        # -- under the given parent
        parent = self.input("Parent").get()
        if parent:
            mc.parent(
                builder.org,
                parent,
            )
        return True

    def user_func_remove_guide(self) -> None:
        """
        This function removes the guide setup - storing all its data
        before doing so.
        """
        # -- Access our guide data. If we cannot get any then we have nothing
        # -- to remove
        guide_data = self.option("GuideData").get()
        if not guide_data:
            return

        # -- Get the linked guide. Again, if there is not a linked guide
        # -- then there is nothing we can do.
        guide_org = guide_data.get("LinkedGuide")
        if not guide_org or not mc.objExists(guide_org):
            return

        # -- Declare the dictionary where we store all the guide data
        guide_xform_data = dict()

        # -- Cycle each control and apply its attribute data
        counter = 1
        while True:
            tag = "Tentacle Control %s" % counter
            node = aniseed_toolkit.run(
                "Find First Child With Tag",
                guide_org,
                tag,
            )
            if not node:
                break

            guide_xform_data[tag] = dict()
            for attr in mc.listAttr(node, k=True):
                guide_xform_data[tag][attr] = mc.getAttr(f"{node}.{attr}")

            # -- Increment the counter so we can find the next control
            counter += 1

        # -- Store all the joint transforms
        joint_transforms = dict()
        start_joint = self.input("Start Joint").get()
        end_joint = self.input("End Joint").get()
        for joint in aniseed_toolkit.run("Get Joints Between", start_joint, end_joint):
            joint_transforms[joint] = mc.xform(
                joint,
                matrix=True,
                query=True,
            )

        # -- Now that we have read all the guide information we can
        # -- delete the guide itself.
        mc.delete(guide_org)

        # -- Finally we store all this data back into the guide data option.
        guide_data["LinkedGuide"] = None
        guide_data["AttributeData"] = guide_xform_data
        guide_data["BoneMatrices"] = joint_transforms
        self.option("GuideData").set(guide_data)

        # -- Finally we restore the joint transforms. This is because when we
        # -- delete the control rig the joints ping back to their pre-constrained
        # -- locations.
        for joint, matrix in joint_transforms.items():
            mc.xform(
                joint,
                m=matrix,
            )



class TentacleBuilder:
    """
    This class is a wrapper class around the blur studios rig build. It simply
    allows for easy access to particular elements in the build and wrangles the
    names etc.
    """
    TAG = "Default"

    def __init__(
        self,
        cv_count: int,
        joint_count: int,
        description: str,
        location: str,
        config: "aniseed.RigConfiguration"
    ):
        
        # -- Store our incoming variables
        self.config = config
        self.cv_count = cv_count
        self.joint_count = joint_count
        self.description = description
        self.location = location
        
        # -- The look up is a variable where we store the nodes 
        # -- "given" name by the blur code, and maps to an mobject
        self.lookup = dict()
        
        # -- This node stores a mapping of only the controls, where the key
        # -- is the blur name and the value is an mobject reference
        self._blur_controls = dict()
        self._final_controls = list()
        
        # -- Build the twist spine and store all the outputs from the blur
        # -- function
        self.artefacts = twistSplineBuilder.makeTwistSpline(
            self.TAG,
            self.cv_count,
            self.joint_count,
            spread=1,
            maxParam=None,
            closed=False,
            singleTangentNode=True,
        )
        
        # -- Start first by populating the lookup - this is important because
        # -- we will internally reference things by the blur name. 
        self._populate_lookup()
        
        # -- Now that we have built the blur rig we need to place various
        # -- nodes under a structure which makes more sense for our style
        # -- of rigging.
        self._construct_wrapping_hierarchy()
        
        # -- We now need to rename all created nodes to align with the naming
        # -- convention of the RigConfiguration requested by the user
        self.resolve_names()
        
        # -- Finally we now need to construct actual aniseed controls to represent
        # -- all the blur controls.
        self.build_controls()

    def _construct_wrapping_hierarchy(self):
        """
        In this function we create a high level organisational node which 
        everything will sit under. We also create a node which will not inherit
        transforms. 
        """
        # -- Create the top level org
        self.org = mc.createNode("transform")

        # -- Create the no transform child
        self.no_transform = mc.createNode("transform")
        mc.setAttr(f"{self.no_transform}.inheritsTransform", False)
        mc.parent(self.no_transform, self.org)
        
        # -- For all the artefacts which are a child of the scene root, we 
        # -- place them under our org or no transform group.
        for node in self._root_artefacts():
            parent = self.org
            if node.startswith("Rig_"):
                parent = self.no_transform
            mc.parent(node, parent)

    def _populate_lookup(self):
        """
        This will cycle over all the created nodes and add an mobject
        reference to them. This is important because we dont want to be 
        constantly managing name changes. 
        """
        nodes = self._root_artefacts()

        for node in nodes[:]:
            nodes.extend(mc.listRelatives(node, ad=True))

        for node in nodes:
            self.lookup[node] = aniseed_toolkit.run("Get MObject", node)

    def _root_artefacts(self):
        """
        This gives us a hard coded list of all teh objects the blur
        code generates at the scene level. This never changes and will
        always be renamed before the next one is created.  
        """
        return [
            f"Ctrl_X_{self.TAG}SplineGlobal_Part",
            f"Org_X_{self.TAG}_Ctrls",
            f"Rig_X_{self.TAG}Spline_Drv",
            f"Org_X_X_{self.TAG}Jnts",

        ]

    def all_nodes(self):
        """
        Return the names of all the objects in the rig
        """
        return [
            m_object
            for m_object in self.lookup.values()
        ]

    def controls(self):
        """
        Returns the names of all the controls in the rig
        """
        return [
            aniseed_toolkit.run("MObject Name", control)
            for control in self._final_controls
        ]

    def mechanicals(self):
        """
        This returns all the nodes in the blur rigs which are nodes relating
        to zero'ing or providing mechanical support to the rig
        """
        return [
            self.lookup[node]
            for node in self.lookup.keys()
            if node.startswith("Hbfr_")
        ]

    def joints(self):
        """
        Return all the nodes which are considered joint deformers in the rig
        """
        return [
            self.lookup[node]
            for node in self.lookup.keys()
            if node.startswith("Dfm_")
        ]

    def joint_names(self):
        """
        Convenience function for returning the names of all the joints
        """
        return [
            self.get_name(joint)
            for joint in self.joints()
        ]

    def control_org(self):
        """
        Returns the org which all the controls reside under
        """
        return self.lookup["Org_X_Default_Ctrls"]

    def joints_org(self):
        """
        Returns the org which all the deformers reside under
        """
        return self.lookup["Org_X_X_DefaultJnts"]

    def rig_mech(self):
        """
        Returns the special blur studios tentacle spline node
        """
        return self.lookup["Rig_X_DefaultSpline_Drv"]

    def get_descriptive(self, node: str):
        """
        This will extract the descriptive element of a blur named object
        """
        return node.split(self.TAG)[-1].replace("_", "")

    def get_name(self, m_object: str):
        """
        Convenience function for returning the name of an mobject
        """
        return aniseed_toolkit.run("MObject Name", m_object)

    def blur_control_names(self):
        return [
            aniseed_toolkit.run("MObject Name", control_target)
            for control_target in self._blur_controls.values()
        ]

    def resolve_names(self):
        """
        This function will cycle through the blur rig and rename each node
        based on the rig configuration.
        """
        classifications = {
            "Org_": "org",
            "Rig_": "org",
            "Hbfr_": "mech",
            "Ctrl_": "mechc",
        }

        node_types = ["transform", "joint"]
        for identifier, m_object in self.lookup.items():

            if not mc.objExists(identifier):
                continue

            if not mc.nodeType(identifier) in node_types:
                continue

            classification = "mech"

            for tag, mapped_tag in classifications.items():
                if identifier.startswith(tag):
                    classification = mapped_tag

            label = identifier.split("_")[2].replace("Default", "")

            name = self.config.generate_name(
                classification=classification,
                description=f"{self.description}{label}",
                location=self.location,
            )

            mc.rename(
                identifier, name
            )

            if classification == "mechc":
                self._blur_controls[identifier] = m_object

    def build_controls(self):
        """
        Construct aniseed controls to wrap the blur rig
        """
        counter = 0
        for identifier, m_object in self.lookup.items():

            object_name = aniseed_toolkit.run("MObject Name", m_object)

            if not mc.nodeType(object_name) == "transform":
                continue

            if not object_name in self.blur_control_names():
                continue

            parent = mc.listRelatives(object_name, parent=True)[0]
            children = mc.listRelatives(object_name, children=True)
            shapes = mc.listRelatives(object_name, shapes=True) or list()
            label = identifier.split("_")[2].replace("Default", "")

            new_control = aniseed_toolkit.run(
                "Create Control",
                description=f"{self.description}{label}",
                location=self.location,
                parent=parent,
                config=self.config,
                shape="core_sphere",
                match_to=object_name,
            )

            counter += 1
            aniseed_toolkit.run(
                "Tag Node",
                new_control.ctl,
                "Tentacle Control %s" % counter
            )

            self._final_controls.append(
                aniseed_toolkit.run(
                    "Get MObject",
                    new_control.ctl,
                )
            )
            desired_channelbox_attributes = mc.listAttr(object_name, k=True) or []

            for custom_attribute in mc.listAttr(object_name, ud=True) or []:
                attr_type = mc.attributeQuery(
                    custom_attribute,
                    node=object_name,
                    attributeType=True,
                )

                additional_options = dict()

                has_min = mc.attributeQuery(
                    custom_attribute,
                    node=object_name,
                    minExists=True,
                )
                has_max = mc.attributeQuery(
                    custom_attribute,
                    node=object_name,
                    maxExists=True,
                )

                if has_min:
                    additional_options["minValue"] = mc.attributeQuery(
                        custom_attribute,
                        node=object_name,
                        min=True,
                    )[0]

                if has_max:
                    additional_options["maxValue"] = mc.attributeQuery(
                        custom_attribute,
                        node=object_name,
                        max=True,
                    )[0]

                mc.addAttr(
                    new_control.ctl,
                    shortName=custom_attribute,
                    attributeType=attr_type,
                    dv=mc.getAttr(f"{object_name}.{custom_attribute}"),
                    k=True,
                    **additional_options
                )

            for attr in mc.listAttr(new_control.ctl, k=True)[:]:
                if attr not in desired_channelbox_attributes:
                    mc.setAttr(f"{new_control.ctl}.{attr}", k=False, cb=False, lock=True)

                else:
                    mc.connectAttr(
                        f"{new_control.ctl}.{attr}",
                        f"{object_name}.{attr}",
                    )

            # -- Finally we need to move the shape nodes over to the new node
            for shape in mc.listRelatives(new_control.ctl, shapes=True):
                mc.delete(shape)

            for shape in mc.listRelatives(object_name, shapes=True) or list():
                mc.parent(shape, new_control.ctl, shape=True, relative=True)
