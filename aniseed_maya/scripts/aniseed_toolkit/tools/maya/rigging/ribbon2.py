import mref
import aniseed_toolkit
import maya.cmds as mc


class RibbonTool(aniseed_toolkit.Tool):

    identifier = "Create Ribbon Setup2"
    classification = "Rigging"
    categories = [
        "Rigging",
    ]

    def run(
        self,
        start_joint,
        end_joint,
        transform_matrices,
        parent=None,
        ribbon=None,
        skin_data=None,
    ):
        ribbon = Ribbon(
            start_joint=start_joint,
            end_joint=end_joint,
            transform_matrices=transform_matrices,
            parent=parent,
            ribbon=ribbon,
            skin_data=skin_data,
        )
        ribbon.build()
        return ribbon


class Ribbon:

    def __init__(self, start_joint, end_joint, transform_matrices, ribbon=None, parent=None, skin_data=None):

        # -- Input attributes
        self.start_joint = start_joint
        self.end_joint = end_joint
        self.transform_matrices = transform_matrices
        self.skin_data = skin_data
        self.parent = parent

        # -- Output attributes
        self.joints = []
        self.follicles = []
        self.driving_transforms = []
        self.driving_joints = []
        self.rotators = []
        self.upvectors = []
        self.org = None
        self.no_transform_org = None
        self.follicle_org = None
        self.ribbon = ribbon
        self.skin = None


    def build(self):


        # -- Get the full chain list
        self.joints = mref.get(
            aniseed_toolkit.run(
                "Get Joints Between",
                self.start_joint,
                self.end_joint,
            ),
        )

        # -- Create the overall org
        self.org = mref.create("transform")
        self.org.match_to(self.joints[0])

        if self.parent:
            self.org.set_parent(self.parent)

        # -- Calculate a reasonable width for the ribbon
        width = aniseed_toolkit.run(
            "Get Chain Length",
            self.start_joint,
            self.end_joint,
        ) * 0.1

        # -- Get the joint positions
        joint_positions = [
            joint.xform(query=True, worldSpace=True, translation=True)
            for joint in self.joints
        ]

        positions = []
        for matrix in self.transform_matrices:
            positions.append(
                [
                    matrix[-4],
                    matrix[-3],
                    matrix[-2],
                ],
            )

        # -- Create the no transform group
        self.no_transform_org = mref.create("transform")
        self.no_transform_org.set_parent(self.org)
        self.no_transform_org.attribute("inheritsTransform").set(False)
        aniseed_toolkit.run(
            "Tag Node",
            self.no_transform_org.full_name(),
            "no_transform",
        )

        # -- Create center curve
        center_curve = mc.curve(
            d=3,
            p=joint_positions,
            name="ribbon_center_crv",
        )

        # -- Duplicate and offset curves left/right
        if not self.ribbon:
            print("we have not been given a ribbon, so we have to make one!")
            curve_left = mc.duplicate(center_curve, name="ribbon_left_crv")[0]
            curve_right = mc.duplicate(center_curve, name="ribbon_right_crv")[0]
            mc.move(width * 0.5, curve_left, x=True, r=True, os=True)
            mc.move(-width * 0.5, curve_right, x=True, r=True, os=True)

            # -- Loft surface
            self.ribbon = mref.get(
                mc.loft(
                    curve_left,
                    curve_right,
                    ch=False,
                    uniform=True,
                    degree=3,
                    name="ribbon_surface",
                )[0],
            )
            # Rebuild strip to proper number of spans
            span_count = len(self.transform_matrices) + 2
            mc.rebuildSurface(self.ribbon.full_name(), ch=0, rpo=1, rt=0, end=1, kr=0, kcp=0, kc=1, sv=span_count, su=0, du=1, tol=0.01, fr=0, dir=2)
        else:
            print("using pre-existing ribbon!")
            self.ribbon = mref.get(self.ribbon)


        self.no_transform_org.add_child(self.ribbon)
        aniseed_toolkit.run(
            "Tag Node",
            self.ribbon.full_name(),
            "ribbon",
        )
        # -- Get surface shape
        ribbon_shape = self.ribbon.shape()

        # -- Group follicles
        self.follicle_org = mref.create(
            "transform",
            name="ribbon_follicles_grp",
            parent=self.no_transform_org.full_name(),
        )

        rotator = None
        upvector = None
        for idx, joint in enumerate(self.joints):
            # -- Create follicle transform + shape properly
            follicle_transform = mref.create(
                'transform',
                name=f"ribbon_follicle_{idx + 1}",
            )
            aniseed_toolkit.run(
                "Tag Node",
                follicle_transform.full_name(),
                "follicle",
            )
            follicle_shape = mref.create(
                'follicle',
                name=f"ribbon_follicle_{idx + 1}Shape",
                parent=follicle_transform.full_name(),
            )

            # -- Connect surface to follicle
            ribbon_shape.attr("local").connect(follicle_shape.attr("inputSurface"))
            ribbon_shape.attr("worldMatrix[0]").connect(follicle_shape.attr("inputWorldMatrix"))

            # -- Connect follicle outputs
            follicle_shape.attr("outTranslate").connect(follicle_transform.attr("translate"))
            follicle_shape.attr("outRotate").connect(follicle_transform.attr("rotate"))

            last_rotator = rotator
            last_upvector = upvector

            rotator = mref.create("transform", parent=follicle_transform.full_name(), name=f"ribbon_rotator_{idx + 1}")
            rotator.match_to(follicle_transform)
            self.rotators.append(rotator)

            upvector = mref.create("transform", parent=follicle_transform.full_name(), name=f"ribbon_upvector_{idx + 1}")
            upvector.match_to(follicle_transform)
            upvector.attr("translateZ").set(10)
            self.upvectors.append(upvector)

            if last_rotator:
                mc.aimConstraint(
                    rotator.full_name(),
                    last_rotator.full_name(),
                    aimVector=[1, 0, 0],
                    upVector=[0, 1, 0],
                    worldUpType="object",
                    worldUpObject=upvector.full_name(),
                    maintainOffset=False,
                )

            # -- Evenly distribute along V
            parameter = float(idx) / (len(self.joints) - 1)
            follicle_shape.attr("parameterU").set(0.5)
            follicle_shape.attr("parameterV").set(parameter)
            self.follicle_org.add_child(follicle_transform)

            # -- Ensure we expose easy access to the follicle
            self.follicles.append(follicle_transform)

        for idx in range(len(self.joints)):

            mc.parentConstraint(
                self.rotators[idx].full_name(), #follicle_transform.full_name(),
                self.joints[idx].full_name(),
                mo=True,
            )

        # -- Delete our temporary items
        try:
            mc.delete(center_curve)
            mc.delete(curve_left)
            mc.delete(curve_right)

        except:
            pass

        # -- Read the guide data to get the control transforms

        for idx, matrix in enumerate(self.transform_matrices):
            driving_transform = mref.create(
                "transform",
                parent=self.org.full_name(),
            )
            aniseed_toolkit.run(
                "Tag Node",
                driving_transform.full_name(),
                "follicle",
            )

            driving_transform.xform(matrix=matrix)
            driving_transform.rename(f"RibbonControl{idx + 1}")
            self.driving_transforms.append(driving_transform)

            # -- Create a joint to skin to
            driving_joint = mref.create("joint", parent=driving_transform.full_name())
            driving_joint.rename(f"RibbonControlJoint{idx + 1}")
            driving_joint.set_matrix(driving_transform.get_matrix(space="world"), space="world")
            self.driving_joints.append(driving_joint)

        # -- Apply the skin data if there is any
        # mc.select([j.full_name() for j in control_joints])
        joint_names = [j.full_name() for j in self.driving_joints]
        ribbon_name = self.ribbon.full_name()
        mc.select(joint_names)
        skin = mc.skinCluster(
            joint_names,
            self.ribbon.full_name(),
            toSelectedBones=True,
        )
        self.skin = mref.get(skin)

        # -- If there is no skin data then we apply a default skin
        if self.skin_data:
            pass