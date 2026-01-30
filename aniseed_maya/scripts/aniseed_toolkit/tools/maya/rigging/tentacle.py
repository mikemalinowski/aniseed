import maya.cmds as mc


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
                 cv_count,
                 rider_count,
                 max_param,
                 spread,
                 closed=False,
                 parent=None):

        # -- Input arguments
        self.description = description
        self.side = side
        self.cv_count = cv_count
        self.rider_count = rider_count
        self.max_param = max_param
        self.spread = spread
        self.closed = closed
        self.parent = parent
        self.config = config

        # -- Output variables
        self.controls = list()
        self.riders = list()
        self.master = None

        # -- Validate all our inputs
        if self.cv_count < 2:
            raise ValueError("Cannot create a TwistSpline with less than 2 CVs")

        if not mc.pluginInfo("TwistSpline", query=True, loaded=True):
            mc.loadPlugin("TwistSpline")

        if self.max_param is None:
            self.max_param = (self.cv_count - 1)

        self.max_param *= 3.0 * self.spread

    # --------------------------------------------------------------------------
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
        control_org = mc.rename(
            mc.createNode("transform"),
            self._config.generate_name(
                classification="org",
                description=self._description + "TwistGroup",
                location=self._location,
            ),
        )
        control_org = crab.create.org(
            description=self.description,
            side=self.side,
            parent=self.parent,
        )

        # -- Create our master control which will contain the aniamtion
        # -- attributes
        self.master = crab.create.control(
            description='%sMaster' % self.description,
            side=self.side,
            shape='cube',
            parent=control_org,
        )

        # -- Add the required attributes to the master control
        crab.utils.organise.add_separator_attr(self.master)

        self.master.addAttr(
            'Offset',
            attributeType='double',
            defaultValue=0.0,
            keyable=True,
        )

        self.master.addAttr(
            'Stretch',
            attributeType='double',
            defaultValue=1.0,
            keyable=True,
            minValue=0.0001,
        )

        self.master.addAttr(
            'Twist',
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
                description=self.description,
                side=self.side,
                parent=self.master,
            )

            controls.append(control_inst)

            # -- Get the org, and position it accordingly
            cv_org = crab.utils.hierarchy.find_above(
                control_inst.cv,
                crab.config.ORG,
            )

            # -- Spread the controls out
            cv_org.setTranslation(
                [
                    self.spread * 3 * idx,
                    0,
                    0,
                ],
            )

        # -- Set the tangent locations
        for idx in range(self.cv_count if self.closed else self.cv_count):

            control_inst = controls[idx]

            in_tangent_org = crab.utils.hierarchy.find_above(
                control_inst.in_tangent,
                crab.config.ORG,
            )

            in_tangent_org.setTranslation(
                [
                    -self.spread,
                    0,
                    0,
                ]
            )

            out_tangent_org = crab.utils.hierarchy.find_above(
                control_inst.out_tangent,
                crab.config.ORG,
            )

            out_tangent_org.setTranslation(
                [
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
        out_twist_node = crab.create.generic(
            node_type='twistTangent',
            description='%sTwistTangentOut' % self.description,
            side=self.side,
            prefix=crab.config.MATH,
        )

        out_tangent.attr('worldMatrix[0]').connect(out_twist_node.inTangent)
        out_tangent.Auto.connect(out_twist_node.auto)
        out_tangent.Smooth.connect(out_twist_node.smooth)
        out_tangent.Weight.connect(out_twist_node.weight)

        if not is_first:
            previous_control.attr('worldMatrix[0]').connect(
                out_twist_node.previousVertex,
            )

        else:
            out_tangent.Smooth.set(0)

        start_control.attr('worldMatrix[0]').connect(
            out_twist_node.currentVertex,
        )
        end_control.attr('worldMatrix').connect(
            out_twist_node.nextVertex,
        )
        out_tangent.Auto.set(1.0)

        # -- Create the input tangent solver
        in_twist_node = crab.create.generic(
            node_type='twistTangent',
            description='%sTwistTangentIn' % self.description,
            side=self.side,
            prefix=crab.config.MATH,
        )

        in_tangent.attr('worldMatrix[0]').connect(in_twist_node.inTangent)
        in_tangent.Auto.connect(in_twist_node.auto)
        in_tangent.Smooth.connect(in_twist_node.smooth)
        in_tangent.Weight.connect(in_twist_node.weight)

        if not is_last:
            next_control.attr('worldMatrix[0]').connect(
                in_twist_node.previousVertex,
            )

        else:
            in_tangent.Smooth.set(0)

        end_control.attr('worldMatrix[0]').connect(
            in_twist_node.currentVertex,
        )

        start_control.attr('worldMatrix[0]').connect(
            in_twist_node.nextVertex,
        )

        in_tangent.Auto.set(1.0)

        in_twist_node.outLinearTarget.connect(
            out_twist_node.inLinearTarget,
        )

        out_twist_node.outLinearTarget.connect(
            in_twist_node.inLinearTarget,
        )

        out_twist_node.out.connect(start_out_marker.translate)
        start_out_marker.attr('parentInverseMatrix[0]').connect(
            out_twist_node.attr('parentInverseMatrix'),
        )

        in_twist_node.out.connect(
            end_in_marker.translate,
        )

        end_in_marker.attr('parentInverseMatrix[0]').connect(
            in_twist_node.attr('parentInverseMatrix'),
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
                previous_control=controls[pre_idx].cv,
                start_control=controls[start_idx].cv,
                end_control=controls[end_idx].cv,
                next_control=controls[next_idx].cv,
                out_tangent=controls[idx].out_tangent,
                in_tangent=controls[(idx + 1) % len(controls)].in_tangent,
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
        joint_org = crab.create.org(
            description='%sRiders' % self.description,
            side=self.side,
            parent=self.parent,
        )

        riders = list()
        rider_xfos = list()

        for i in range(self.rider_count):

            rider_xfo = crab.create.generic(
                node_type='transform',
                description='%sRiderXfo' % self.description,
                side=self.side,
                prefix=crab.config.MARKER,
                parent=joint_org,
            )

            rider = crab.create.generic(
                node_type='joint',
                description='%sRider' % self.description,
                side=self.side,
                prefix=crab.config.MECHANICAL,
                parent=rider_xfo,
            )

            rider.radius.set(1.2)
            rider.drawStyle.set(2)
            rider_xfo.displayLocalAxis.set(False)

            riders.append(rider)
            rider_xfos.append(rider_xfo)

        # -- Create the constraint node
        constraint = crab.create.generic(
            node_type='riderConstraint',
            prefix=crab.config.MECHANICAL,
            description='%sRiderConstraint' % self.description,
            side=self.side,
        )

        # -- Hook up our master control attributes to our
        # -- constraint attributes
        master_control.Offset.connect(constraint.globalOffset)
        master_control.Stretch.connect(constraint.globalSpread)
        master_control.Twist.connect(constraint.globalTwist)

        # -- Inform the constraint whether we're a closed
        # -- look constraint
        constraint.useCycle.set(int(self.closed))

        spline.outputSpline.connect(constraint.attr('inputSplines[0].spline'))

        for i in range(len(riders)):
            if len(riders) == 1:
                constraint.attr('params[%s].param' % i).set(0.5)

            else:
                constraint.attr('params[%s].param' % i).set(
                    i / (self.rider_count - 1.0)
                )

            rider_xfos[i].attr('parentInverseMatrix[0]').connect(
                constraint.attr('params[%s].parentInverseMatrix' % i),
            )

            for type_ in ['translate', 'rotate', 'scale']:
                constraint.attr('outputs[%s].%s' % (i, type_)).connect(
                    rider_xfos[i].attr(type_),
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
        spline = crab.create.generic(
            node_type='twistSpline',
            description=self.description + 'SplineShape',
            side=self.side,
            prefix=crab.config.MECHANICAL,
        )
        spline_xfo = spline.getParent()
        spline_xfo.rename(
            crab.config.name(
                description=self.description + 'Spline',
                side=self.side,
                prefix=crab.config.MECHANICAL,
            )
        )
        spline_xfo.setParent(self.parent)
        spline_xfo.visibility.set(False)

        # -- Hook up the in tangents, ignoring the first one
        for idx, in_marker in enumerate(used_in_markers):
            in_marker.attr('worldMatrix[0]').connect(
                spline.attr('vertexData[%s].inTangent' % (idx + 1)),
            )

        for idx, out_marker in enumerate(used_out_markers):
            # -- Now hook up the out tangents, and skip the last
            out_marker.attr('worldMatrix[0]').connect(
                spline.attr('vertexData[%s].outTangent' % idx),
            )

        for u in range(used_cvs):

            i = u % used_cvs

            controls[i].cv.attr('worldMatrix[0]').connect(
                spline.attr('vertexData[%s].controlVertex' % u),
            )

            controls[i].cv.Pin.connect(
                spline.attr('vertexData[%s].paramWeight' % u),
            )

            if u != i:
                # -- The param Value needs an offset if we're at the
                # -- last connection of a closed spline
                add_node = crab.create.generic(
                    node_type='addDoubleLinear',
                    description='%sAdd' % self.description,
                    side=self.side,
                    prefix=crab.config.MATH,
                )

                add_node.input2.set(self.max_param)
                controls[i].cv.PinParam.connect(add_node.input1)

                add_node.output.connect(
                    spline.attr('vertexData[%s].paramValue' % u),
                )

            else:
                controls[i].cv.PinParam.connect(
                    spline.attr('vertexData[%s].paramValue' % u),
                )

                controls[i].cv.PinParam.set(
                    (u * self.max_param) / (used_cvs - 1.0),
                )

            controls[i].twist.UseTwist.connect(
                spline.attr('vertexData[%s].twistWeight' % u),
            )

            controls[i].twist.rotateX.connect(
                spline.attr('vertexData[%s].twistValue' % u),
            )

        controls[0].cv.Pin.set(1)
        controls[0].twist.UseTwist.set(1)

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