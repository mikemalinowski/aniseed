import aniseed
import aniseed_toolkit
from maya import cmds
import maya.cmds as mc
import qtility

import functools

# ------------------------------------------------------------------------------
class TentacleComponent(aniseed.RigComponent):

    identifier = 'Limb : Tentacle2'
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

        # self.options.description = 'Tentacle'
        # self.options.side = crab.config.MIDDLE
        # self.options.cv_count = 4
        # self.options.joint_count = 8
        # self.options.length = 20
        # self.options.apply_spaceswitches = True

    # --------------------------------------------------------------------------
    def create_skeleton(self, joint_count=None, parent=None):
        """
        This is where you should build your skeleton. `parent` is the node
        your build skeleton should reside under and it will never be None.

        :param parent: Node to parent your skeleton under
        :type parent: pm.nt.DagNode

        :return: True if successful
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
        increment = 10.0 / float(joint_count + 1)

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
            menu["Create Joints"] = functools.partial(self.create_skeleton)
            return menu
        menu["Create Guide"] = functools.partial(self.create_guide)

        return menu

    # --------------------------------------------------------------------------
    def create_guide(self, parent=None):
        """
        This function allows you to build a guide element.

        :param parent: Parent node to build the rig under

        :return:
        """

        parent = None
        joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Start Joint").get(),
            self.input("End Joint").get(),
        )
        chain_length = aniseed_toolkit.run(
            "Get Chain Length",
            self.input("Start Joint").get(),
            self.input("End Joint").get(),
        )

        descriptive_prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        cv_count = self.option("Control Count").get()

        tentacle_builder = TentacleBuilder(
            description=f"{descriptive_prefix}Guide",
            side=location,
            cv_count=cv_count,
            rider_count=len(joints),
            max_param=None,
            spread=(chain_length / cv_count) / 3.0,
            parent=parent,
            config=self.config,
        )

        # -- Create the tentacle
        tentacle_builder.create()
        return
        # -- Zero the guide against the joint
        tentacle_builder.master.setMatrix(pm.dt.Matrix())

        for rider in tentacle_builder.riders:
            self.tag(
                rider,
                'TentacleRiderGuide',
            )

        for guide in tentacle_builder.all_controls():

            guide_org = crab.utils.hierarchy.find_above(
                guide,
                crab.config.ORG,
            )
            guide.setParent(guide_org.getParent())
            pm.delete(guide_org)

            guide.rename(
                guide.name().replace(
                    crab.config.CONTROL + '_',
                    crab.config.GUIDE + '_',
                )
            )

            self.tag(
                guide,
                'TentacleControlGuide',
            )

            for shape in guide.getShapes():

                # -- Set the display colour
                shape.overrideEnabled.set(True)
                shape.overrideRGBColors.set(True)

                shape.overrideColorR.set(0)
                shape.overrideColorG.set(1)
                shape.overrideColorB.set(0)

        self.tag(
            tentacle_builder.master,
            'TentacleMasterGuide',
        )

        # -- Reparent the cv controls
        all_cv_controls = [ctl.cv for ctl in tentacle_builder.controls]
        parent = None

        for cv_control in all_cv_controls:
            if parent:
                cv_control.setParent(parent)

            parent = cv_control

        for control_inst in tentacle_builder.controls:
            cmds.setAttr(f"{control_inst}.twist", False)

        return True
    #
    # # --------------------------------------------------------------------------
    # def link_guide(self):
    #     """
    #     This should perform the required steps to have the skeletal
    #     structure driven by the guide (if the guide is implemented). This
    #     will then be triggered by Rig.edit process.
    #
    #     :return: None
    #     """
    #     guide_riders = self.find('TentacleRiderGuide')
    #     joints = self.find('TentacleJoint')
    #
    #     if len(guide_riders) != len(joints):
    #         raise Exception('Miss-match between riders and joints')
    #
    #     for guide, joint in zip(guide_riders, joints):
    #
    #         try:
    #             pm.delete(joint.getChildren(type='parentConstraint'))
    #
    #         except: pass
    #
    #         pm.parentConstraint(
    #             guide,
    #             joint,
    #             maintainOffset=False,
    #         )
    #         joint.template.set(True)
    #
    #     return True
    #
    # # --------------------------------------------------------------------------
    # def unlink_guide(self):
    #     """
    #     This should perform the operation to unlink the guide from the
    #     skeleton, leaving the skeleton completely free of any ties
    #     between it and the guide.
    #
    #     This is run as part of the Rig.build process.
    #
    #     :return: None
    #     """
    #
    #     for joint in self.find('TentacleJoint'):
    #         constraints = joint.getChildren(type='parentConstraint')
    #
    #         if constraints:
    #             pm.delete(constraints)
    #
    #         joint.template.set(False)
    #
    #     return True
    #
    # # --------------------------------------------------------------------------
    # def create_rig(self, parent):
    #     """
    #     This should create your animation rig for this segment. The parent
    #     will be a pre-constructed crabSegment transform node and the guide
    #     will be an instance of this class centered on the guide.
    #
    #     :param parent: Parent node to build the rig under
    #
    #     :return:
    #     """
    #
    #     joints = self.find('TentacleJoint')
    #
    #     length = 0
    #     for joint in joints:
    #         # -- Skip the first joint
    #         if joint == joints[0]:
    #             continue
    #
    #         length += joint.getTranslation().length()
    #
    #     tentacle_builder = TentacleBuilder(
    #         description=self.options.description,
    #         side=self.options.side,
    #         cv_count=self.options.cv_count,
    #         rider_count=self.options.joint_count,
    #         max_param=None,
    #         spread=(length / (self.options.cv_count - 1)) / 3.0,
    #         parent=parent,
    #     )
    #
    #     # -- Create the tentacle
    #     tentacle_builder.create()
    #
    #     for rider in tentacle_builder.riders:
    #         self.tag(
    #             rider,
    #             'TentacleRider',
    #         )
    #
    #     riders = self.find('TentacleRider')
    #
    #     if len(riders) != len(joints):
    #         raise Exception('Miss-match between riders and joints')
    #
    #     for rider, joint in zip(riders, joints):
    #         self.bind(
    #             joint,
    #             rider,
    #             maintainOffset=False,
    #         )
    #
    #     self.tag(
    #         tentacle_builder.master,
    #         'TentacleMaster',
    #     )
    #
    #     # -- Tag all our controls
    #     for control in tentacle_builder.all_controls():
    #         self.tag(
    #             control,
    #             'TentacleControl',
    #         )
    #
    #     # -- Match the master control
    #     master_org = crab.utils.hierarchy.find_above(
    #         self.find_first('TentacleMaster'),
    #         crab.config.ORG,
    #     )
    #
    #     master_org.setMatrix(
    #         self.find_first('TentacleMasterGuide').getMatrix(worldSpace=True),
    #         worldSpace=True,
    #     )
    #
    #     # -- Now we need to match all our rig controls to our guide controls
    #     for guide, control in zip(self.find('TentacleControlGuide'), self.find('TentacleControl')):
    #
    #         if control == tentacle_builder.master:
    #             continue
    #
    #         # -- Get the control org
    #         control_org = crab.utils.hierarchy.find_above(
    #             control,
    #             crab.config.ORG,
    #         )
    #
    #         # -- Match the control org to the guide item
    #         control_org.setMatrix(
    #             guide.getMatrix(worldSpace=True),
    #             worldSpace=True,
    #         )
    #
    #         # -- Match any attributes
    #         for attr in guide.listAttr(ud=True, k=True):
    #             attr_name = attr.name(includeNode=False)
    #             if not attr.isLocked():
    #
    #                 # -- Skip this attribute as its a setup attribute and
    #                 # -- defined dynamically
    #                 if attr_name == 'PinParam':
    #                     continue
    #
    #                 if control.hasAttr(attr_name):
    #                     target_attr = control.attr(attr_name)
    #                     target_attr.set(attr.get())
    #
    #     if self.options.apply_spaceswitches:
    #         # -- Reparent the cv controls
    #         all_cv_controls = [ctl.cv for ctl in tentacle_builder.controls]
    #         parent_control = None
    #
    #         for cv_control in all_cv_controls:
    #
    #             if parent_control:
    #                 crab.plugins.behaviours.spaceswitch.SpaceSwitch.create(
    #                     crab.config.get_description(cv_control) + 'SpaceSwitch',
    #                     side=self.options.side,
    #                     target=cv_control,
    #                     spaces=[
    #                         parent_control,
    #                         pm.PyNode(
    #                             [
    #                                 parent
    #                                 for parent in cv_control.longName().split('|')
    #                                 if crab.config.CONTROL in parent
    #                             ][0]
    #                         )
    #                     ],
    #                     labels=['Previous Control', 'World'],
    #                     applied_space='Previous Control',
    #                     parent_label='Root',
    #                 )
    #
    #             parent_control = cv_control
    #
    #     return True
    #
    #
    #
    #
    #
    #
    #
    #
    #
    #

























# ------------------------------------------------------------------------------
class Control(object):
    """
    Represents a convience class for accessing the a control and its
    sub-controls to make it easier to build a tentacle with
    """
    def __init__(self, description, side, config, parent=None):
        self.cv = None
        self.twist = None
        self.config = config
        self.in_tangent = None
        self.out_tangent = None
        self.in_marker = None
        self.out_marker = None
        self.description = description

        self._create(description, side, parent=parent)

    # --------------------------------------------------------------------------
    @property
    def controls(self):
        return [
            self.cv,
            self.twist,
            self.in_tangent,
            self.out_tangent,
        ]

    # --------------------------------------------------------------------------
    @property
    def tangents(self):
        return [self.in_tangent, self.out_tangent]

    # --------------------------------------------------------------------------
    @property
    def tangent_markers(self):
        return [self.in_marker, self.out_marker]

    # --------------------------------------------------------------------------
    def _create(self, description, side, parent=None):

        # -- Create our cv control

        self.cv = aniseed_toolkit.run(
            "Create Control",
            description=f"{self.description}Cv",
            location=side,
            parent=parent,
            shape="core_cube",
            config=self.config,
        )

        cmds.addAttr(
            self.cv.ctl,
            shortName='ShowTangents',
            attributeType='double',
            defaultValue=0.0,
            minValue=0.0,
            maxValue=1.0,
            keyable=True,
        )

        cmds.addAttr(
            self.cv.ctl,
            shortName='Pin',
            attributeType='double',
            defaultValue=0.0,
            minValue=0.0,
            maxValue=1.0,
            keyable=True,
        )

        cmds.addAttr(
            self.cv.ctl,
            shortName='PinParam',
            attributeType='double',
            defaultValue=0.0,
            minValue=0.0,
            keyable=True,
        )

        # -- Now create the twist control
        self.twist = aniseed_toolkit.run(
            "Create Control",
            description='%sTwist' % description,
            location=side,
            parent=self.cv.ctl,
            match_to=self.cv.ctl,
            shape='pin',
            config=self.config,
            # lock_list='tx;ty;tz;ry;rz;sx;sy;sz',
            # hide_list='tx;ty;tz;ry;rz;sx;sy;sz;v',
        )

        cmds.addAttr(
            self.twist.ctl,
            shortName='UseTwist',
            attributeType='double',
            defaultValue=0.0,
            minValue=0.0,
            maxValue=1.0,
            keyable=True,
        )

        self.in_tangent = aniseed_toolkit.run(
            "Create Control",
            description='%sInTangent' % description,
            location=side,
            parent=self.cv.ctl,
            shape='core_sphere',
            config=self.config,
        )

        self.out_tangent = aniseed_toolkit.run(
            "Create Control",
            description='%sOutTangent' % description,
            location=side,
            parent=self.cv.ctl,
            shape='core_sphere',
            config=self.config,
        )

        for tangent_ctl in self.tangents:

            cmds.connectAttr(
                f"{self.cv.ctl}.ShowTangents",
                f"{tangent_ctl.ctl}.visibility",
            )

            cmds.addAttr(
                tangent_ctl.ctl,
                shortName='Auto',
                attributeType='double',
                defaultValue=1.0,
                minValue=0.0,
                maxValue=1.0,
                keyable=True,
            )

            cmds.addAttr(
                tangent_ctl.ctl,
                shortName='Smooth',
                attributeType='double',
                defaultValue=1.0,
                minValue=0.0,
                maxValue=1.0,
                keyable=True,
            )

            cmds.addAttr(
                tangent_ctl.ctl,
                shortName='Weight',
                attributeType='double',
                defaultValue=1.0,
                minValue=0.0001,
                maxValue=5.0,
                keyable=True,
            )

        # -- Create the tangent markers
        self.in_marker = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="TODOMech",
            description='%sInTangentMarker' % description,
            location=side,
            match_to=self.in_tangent.ctl,
            parent=self.cv.ctl,
            config=self.config,
        )

        self.out_marker = aniseed_toolkit.run(
            "Create Basic Transform",
            classification="TODOMech",
            description='%sOutTangentMarker' % description,
            location=side,
            match_to=self.out_tangent.ctl,
            parent=self.cv.ctl,
            config=self.config,
        )

        for tangent_marker in self.tangent_markers:
            cmds.setAttr(f"{tangent_marker}.overrideEnabled", True)
            cmds.setAttr(f"{tangent_marker}.overrideDisplayType", 2)
            cmds.setAttr(f"{tangent_marker}.visibility", False)

        # -- Finally we create the guide lines
        self.create_line_link(
            self.in_marker,
            self.cv.ctl,
            description=description,
            side=side,
            parent=self.in_marker,
        )

        self.create_line_link(
            self.out_marker,
            self.cv.ctl,
            description=description,
            side=side,
            parent=self.out_marker,
        )

    # --------------------------------------------------------------------------
    @classmethod
    def create_line_link(cls,
                         source,
                         destination,
                         description,
                         side,
                         parent=None):
        """
        Creates a line (curve) link between the source and the destination
        objects. The curve may optionally be a child of a given node.

        :param source: Node from which the curve should start from. This
            is the default parent if not parent is given.
        :type source: pm.nt.PyNode

        :param destination: The final point the curve should reach to
        :type destination: pm.nt.PyNode

        :param description: Descriptive prefix to assign to our line objects
        :type description: str

        :param side: Location (LF, RT, MD) of our line
        :type side: str

        :param parent: Optional node which should be the parent of the
            curve. If omitted the source node will be used
        :type parent: pm.PyNode or None

        :return:pm.nt.NurbsCurve
        """
        # -- Ensure we have a parent to utilise
        parent = parent or source

        # -- Create a linear curve with two points
        curve_xfo = cmds.curve(
            d=1,
            p=([0, 0, 0], [0, 0, 1]),
            k=(0, 1),
        )

        # -- Get the shape
        curve = cmds.listRelatives(curve_xfo, children=True)[0] #.getShape()

        # -- Parent the curve under the source node (or the parent)
        cmds.parent(
            curve,
            parent,
            relative=True,
            shape=True,
            nc=True,
        )

        # -- Delete the unused transform
        cmds.delete(curve_xfo)

        # -- Now we cycle between the destination and the source and hook
        # -- up the cv data
        for idx, node in enumerate([destination, source]):

            # -- If the node is the parent, we do not need to do any
            # -- connections as we'll get it for free
            # TODO -----------------------------------------------------------------------------------------------------------
            if node == parent:
                piv = cmds.xform(
                    source,
                    q=True,
                    rotatePivot=True,
                    objectSpace=True,
                )
                cmds.setAttr(
                    f"{curve}.controlPoints[{idx}]",
                    *piv
                )

            else:

                point_mat_node = cmds.createNode('pointMatrixMult')
                inv_mat_node = cmds.createNode('pointMatrixMult')

                cmds.connectAttr(
                    f"{node}.worldMatrix[0]",
                    f"{point_mat_node}.inMatrix",
                    force=True
                )

                cmds.connectAttr(
                    f"{parent}.worldInverseMatrix",
                    f"{inv_mat_node}.inMatrix",
                    force=True,
                )

                cmds.connectAttr(
                    f"{point_mat_node}.output",
                    f"{inv_mat_node}.inPoint",
                    force=True,
                )

                cmds.connectAttr(
                    f"{inv_mat_node}.output",
                    f"{curve}.controlPoints[%s]" % idx,
                    force=True,
                )

                cmds.setAttr(f"{point_mat_node}.isHistoricallyInteresting", False)
                cmds.setAttr(f"{inv_mat_node}.isHistoricallyInteresting", False)

        cmds.setAttr(f"{curve}.overrideEnabled", True)
        cmds.setAttr(f"{curve}.overrideColor", 3)
        cmds.rename(curve, f"{parent}Shape")

        return curve

# ------------------------------------------------------------------------------
class TentacleBuilder(object):
    """
    :param description: Prefix for all the controls to allow them be
        collectively identified.
    :type description: str

    :param side: What side identifier should be assigned to the control
    :type side: str

    :param cv_count: The amount of cv's the spline should have
    :type cv_count: int

    :param spread: The distance between each control object (including the
        tangent controls)
    :type spread: float

    :param closed: Whether the spline should be a closed loop
    :type closed: bool
    """
    def __init__(self,
                 description,
                 side,
                 config,
                 cv_count,
                 rider_count,
                 max_param,
                 spread,
                 closed=False,
                 parent=None):

        # -- Input arguments
        self.config = config
        self.description = description
        self.side = side
        self.cv_count = cv_count
        self.rider_count = rider_count
        self.max_param = max_param
        self.spread = spread
        self.closed = closed
        self.parent = parent

        # -- Output variables
        self.controls = list()
        self.riders = list()
        self.master = None

        # -- Validate all our inputs
        if self.cv_count < 2:
            raise ValueError("Cannot create a TwistSpline with less than 2 CVs")

        if not cmds.pluginInfo("TwistSpline", query=True, loaded=True):
            cmds.loadPlugin("TwistSpline")

        if self.max_param is None:
            self.max_param = (self.cv_count - 1)

        self.max_param *= 3.0 * self.spread

    def all_controls(self):
        controls = [self.master]

        for control_instance in self.controls:
            controls.extend(control_instance.controls)

        return controls

    # --------------------------------------------------------------------------
    def create_controls(self):
        """
        Creates a layout of controls for the spline

        :return:
        """
        # -- Create the org which we'll place all the controls
        # -- under
        control_org = aniseed_toolkit.run(
            "Create Basic Transform",
            classification=self.config.organisational,
            description="TODOTentacleOrg",
            location=self.side,
            parent=self.parent,
            config=self.config,
        )

        # -- Create our master control which will contain the aniamtion
        # -- attributes
        self.master = aniseed_toolkit.run(
            "Create Control",
            description=f"Master{self.description}",
            location=self.side,
            parent=control_org,
            shape="core_cube",
            config=self.config,
            shape_scale=20.0,
        )

        cmds.addAttr(
            self.master.ctl,
            shortName='Offset',
            attributeType='double',
            defaultValue=0.0,
            keyable=True,
        )

        cmds.addAttr(
            self.master.ctl,
            shortName='Stretch',
            attributeType='double',
            defaultValue=1.0,
            keyable=True,
            minValue=0.0001,
        )

        cmds.addAttr(
            self.master.ctl,
            shortName='Twist',
            attributeType='double',
            defaultValue=0.0,
            keyable=True,
        )

        # -- Create lists to collect everything in
        controls = []

        # -- Cycle over our cv's so we can generate the right
        # -- set of controls
        for idx in range(self.cv_count):
            control_inst = Control(
                description=f"{self.description}CvCtl{idx}",
                side=self.side,
                parent=self.master.ctl,
                config=self.config,
            )
            controls.append(control_inst)

            # -- Get the org, and position it accordingly
            cv_org = control_inst.cv.org

            # -- Spread the controls out
            cmds.xform(
                cv_org,
                translation=[
                    self.spread * 3 * idx,
                    0,
                    0,
                ]
            )

        # -- Set the tangent locations
        for idx in range(self.cv_count if self.closed else self.cv_count):

            control_inst = controls[idx]

            in_tangent_org = control_inst.in_tangent.org

            cmds.xform(
                in_tangent_org,
                translation=[
                    -self.spread,
                    0,
                    0,
                ]
            )

            out_tangent_org = control_inst.out_tangent.org

            cmds.xform(
                out_tangent_org,
                translation=[
                    self.spread,
                    0,
                    0,
                ],
            )

        # -- Store the controls in an instance variable
        # -- for external use
        self.controls = controls

        return self.controls, self.master

    # --------------------------------------------------------------------------
    def setup_individual_tangent(self,
                                 previous_control,
                                 start_control,
                                 end_control,
                                 next_control,
                                 out_tangent,
                                 in_tangent,
                                 start_out_marker,
                                 end_in_marker,
                                 is_first=False,
                                 is_last=False):

        # -- Create the output tangent solver
        out_twist_node = cmds.createNode('twistTangent')

        cmds.connectAttr(
            f"{out_tangent}.worldMatrix[0]",
            f"{out_twist_node}.inTangent",
        )

        cmds.connectAttr(
            f"{out_tangent}.Auto",
            f"{out_twist_node}.auto",
        )

        cmds.connectAttr(
            f"{out_tangent}.Smooth",
            f"{out_twist_node}.smooth",
        )

        cmds.connectAttr(
            f"{out_tangent}.Weight",
            f"{out_twist_node}.weight",
        )

        if not is_first:
            cmds.connectAttr(
                f"{previous_control}.worldMatrix[0]",
                f"{out_twist_node}.previousVertex",
            )

        else:
            cmds.setAttr(f"{out_tangent}.Smooth", 0)

        cmds.connectAttr(
            f"{start_control}.worldMatrix[0]",
            f"{out_twist_node}.currentVertex",
        )

        cmds.connectAttr(
            f"{end_control}.worldMatrix",
            f"{out_twist_node}.nextVertex",
        )
        cmds.setAttr(f"{out_tangent}.Auto", 1)

        # -- Create the input tangent solver
        in_twist_node = cmds.createNode('twistTangent')

        cmds.connectAttr(
            f"{in_tangent}.worldMatrix[0]",
            f"{in_twist_node}.inTangent",
        )

        cmds.connectAttr(
            f"{in_tangent}.Auto",
            f"{in_twist_node}.auto",
        )

        cmds.connectAttr(
            f"{in_tangent}.Smooth",
            f"{in_twist_node}.smooth",
        )

        cmds.connectAttr(
            f"{in_tangent}.Weight",
            f"{in_twist_node}.weight",
        )

        if not is_last:
            cmds.connectAttr(
                f"{next_control}.worldMatrix[0]",
                f"{in_twist_node}.previousVertex",
            )

        else:
            cmds.setAttr(f"{in_tangent}.Smooth", 0)


        cmds.connectAttr(
            f"{end_control}.worldMatrix[0]",
            f"{in_twist_node}.currentVertex",
        )
        cmds.connectAttr(
            f"{start_control}.worldMatrix[0]",
            f"{in_twist_node}.nextVertex",
        )

        cmds.setAttr(f"{in_tangent}.Auto", 1)

        cmds.connectAttr(
            f"{in_twist_node}.outLinearTarget",
            f"{out_twist_node}.inLinearTarget"
        )

        cmds.connectAttr(
            f"{out_twist_node}.outLinearTarget",
            f"{in_twist_node}.inLinearTarget"
        )

        cmds.connectAttr(
            f"{out_twist_node}.out",
            f"{start_out_marker}.translate"
        )

        cmds.connectAttr(
            f"{start_out_marker}.parentInverseMatrix[0]",
            f"{out_twist_node}.parentInverseMatrix"
        )

        cmds.connectAttr(
            f"{in_twist_node}.out",
            f"{end_in_marker}.translate"
        )
        cmds.connectAttr(
            f"{end_in_marker}.parentInverseMatrix[0]",
            f"{in_twist_node}.parentInverseMatrix"
        )

    # --------------------------------------------------------------------------
    def create_tangent_segments(self, controls):
        """
        Hooks up the connections ebtween all the controls and tangent
        controls to allow them to behave in the way we expect.

        :param controls:

        :return:
        """
        segment_count = len(controls) if self.closed else (len(controls) - 1)

        for idx in range(segment_count):

            # -- Determine if this is the first control
            is_first = idx == 0 and not self.closed

            # -- Determine if this is the last control
            is_last = idx == len(controls) - 2 and not self.closed

            pre_idx = idx - 1
            start_idx = idx
            end_idx = (idx + 1) % len(controls)
            next_idx = (idx + 2) % len(controls)

            self.setup_individual_tangent(
                previous_control=controls[pre_idx].cv.ctl,
                start_control=controls[start_idx].cv.ctl,
                end_control=controls[end_idx].cv.ctl,
                next_control=controls[next_idx].cv.ctl,
                out_tangent=controls[idx].out_tangent.ctl,
                in_tangent=controls[(idx + 1) % len(controls)].in_tangent.ctl,
                start_out_marker=controls[idx].out_marker,
                end_in_marker=controls[(idx + 1) % len(controls)].in_marker,
                is_first=is_first,
                is_last=is_last,
            )

    # --------------------------------------------------------------------------
    def create_riders(self,
                      spline,
                      master_control):
        """
        :param spline:
        :param master_control:
        :return:
        """

        # -- Create the org which we'll place all the controls
        # -- under
        joint_org = aniseed_toolkit.run(
            "Create Basic Transform",
            classification=self.config.organisational,
            description="TODORidersOrg",
            location=self.side,
            parent=self.parent,
            config=self.config,
        )

        riders = list()
        rider_xfos = list()

        for i in range(self.rider_count):
            rider_xfo = aniseed_toolkit.run(
                tool_name="Create Basic Transform",
                classification="MECH",
                description='%sRiderXfo' % self.description,
                location=self.side,
                parent=joint_org,
                config=self.config,
            )

            rider = aniseed_toolkit.run(
                tool_name="Create Joint",
                description='%sRider' % self.description,
                location=self.side,
                parent=rider_xfo,
                config=self.config,
            )

            cmds.setAttr(f"{rider}.radius", 1.2)
            cmds.setAttr(f"{rider}.drawStyle", 2)
            cmds.setAttr(f"{rider_xfo}.displayLocalAxis", False)

            riders.append(rider)
            rider_xfos.append(rider_xfo)

        # -- Create the constraint node
        constraint = cmds.createNode('riderConstraint')

        # -- Hook up our master control attributes to our
        # -- constraint attributes
        cmds.connectAttr(
            f"{master_control.ctl}.Offset",
            f"{constraint}.globalOffset",
        )

        cmds.connectAttr(
            f"{master_control.ctl}.Stretch",
            f"{constraint}.globalSpread",
        )
        #
        # cmds.connectAttr(
        #     f"{master_control.ctl}.Twist",
        #     f"{constraint}.globalTwist",
        # )

        # -- Inform the constraint whether we're a closed
        # -- look constraint
        cmds.setAttr(f"{constraint}.useCycle", int(self.closed))
        cmds.connectAttr(
            f"{spline}.outputSpline",
            f"{constraint}.inputSplines[0].spline",
        )

        for i in range(len(riders)):
            if len(riders) == 1:
                cmds.setAttr(f"{constraint}.params[{i}].param", 0.5)

            else:
                cmds.setAttr(
                    f"{constraint}.params[{i}].param",
                    i / (self.rider_count - 1.0),
                )

            cmds.connectAttr(
                f"{rider_xfos[i]}.parentInverseMatrix[0]",
                f"{constraint}.params[{i}].parentInverseMatrix",
            )


            for type_ in ['translate', 'rotate', 'scale']:
                cmds.connectAttr(
                    f"{constraint}.outputs[{i}].{type_}",
                    f"{rider_xfos[i]}.{type_}"
                )

        return riders

    # --------------------------------------------------------------------------
    def generate_spline(self, controls):
        cv_count = len(controls)
        shift = 0 if self.closed else 1
        used_cvs = cv_count + 1 - shift

        used_out_markers = [c.out_marker for c in controls][:-1]
        used_in_markers = [c.in_marker for c in controls][1:]

        # -- Create the spline
        spline = cmds.createNode('twistSpline')
        spline_xfo = cmds.rename(
            cmds.listRelatives(spline, parent=True)[0],
            self.config.generate_name(
                description=self.description + 'Spline',
                location=self.side,
                classification="TODOMECH",
            ),
        )
        spline = cmds.listRelatives(spline_xfo, children=True)[0]
        if self.parent:
            cmds.parent(spline_xfo, self.parent)
        cmds.setAttr(
            f"{spline_xfo}.visibility", False
        )

        # -- Hook up the in tangents, ignoring the first one
        for idx, in_marker in enumerate(used_in_markers):
            cmds.connectAttr(
                f"{in_marker}.worldMatrix[0]",
                f"{spline}.vertexData[{idx + 1}].inTangent",
            )

        for idx, out_marker in enumerate(used_out_markers):
            cmds.connectAttr(
                f"{out_marker}.worldMatrix[0]",
                f"{spline}.vertexData[{idx + 1}].outTangent",
            )

        for u in range(used_cvs):

            i = u % used_cvs
            cmds.connectAttr(
                f"{controls[i].cv.ctl}.worldMatrix[0]",
                f"{spline}.vertexData[{u}].controlVertex",
            )
            cmds.connectAttr(
                f"{controls[i].cv.ctl}.Pin",
                f"{spline}.vertexData[{u}].paramWeight",
            )

            if u != i:
                # -- The param Value needs an offset if we're at the
                # -- last connection of a closed spline
                add_node = cmds.createNode('addDoubleLinear')

                cmds.setAttr(f"{add_node}.input2", self.max_param)


                cmds.connectAttr(
                    f"{controls[i].cv.ctl}.PinParam",
                    f"{add_node}.input1",
                )

                cmds.connectAttr(
                    f"{add_node}.output",
                    f"{spline}.vertexData[{u}].paramValue",
                )

            else:
                cmds.connectAttr(
                    f"{controls[i].cv.ctl}.PinParam",
                    f"{spline}.vertexData[{u}].paramValue",
                )
                cmds.setAttr(
                    f"{controls[i].cv.ctl}.PinParam",
                    (u * self.max_param) / (used_cvs - 1.0)
                )

            cmds.connectAttr(
                f"{controls[i].twist.ctl}.UseTwist",
                f"{spline}.vertexData[{u}].twistWeight",
            )

            cmds.connectAttr(
                f"{controls[i].twist.ctl}.rotateX",
                f"{spline}.vertexData[{u}].twistValue",
            )

        cmds.setAttr(f"{controls[0].cv.ctl}.Pin", 1)
        cmds.setAttr(f"{controls[0].twist.ctl}.UseTwist", 1)

        return spline

    # --------------------------------------------------------------------------
    def create(self):

        controls, master = self.create_controls()

        self.create_tangent_segments(controls)

        spline = self.generate_spline(controls)

        self.riders = self.create_riders(
            spline,
            master,
        )

        return spline
