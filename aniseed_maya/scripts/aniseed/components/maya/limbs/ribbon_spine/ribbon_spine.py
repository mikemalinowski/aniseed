import os
import mref
import typing
import qtility
import aniseed
import aniseed_toolkit
from maya import cmds


class RibbonSpine(aniseed.RigComponent):

    identifier = "Limb : Ribbon Spine"
    icon = os.path.join(
        os.path.dirname(__file__),
        "icon.png",
    )
    default_length = 10
    def __init__(self, *args, **kwargs):
        super(RibbonSpine, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Root Joint",
            value="",
            group="Joint Requirements",
        )

        self.declare_input(
            name="Tip Joint",
            value="",
            group="Joint Requirements",
        )

        self.declare_option(
            name="Descriptive Prefix",
            value="Spine",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            value="core_circle",
            group="Visuals",
        )

        self.declare_option(
            name="Control Count",
            value=4,
            group="Behaviour",
            pre_expose=True,
        )

        self.declare_option(
            name="Orient Controls To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Lock End Orientations To Controls",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="GuideData",
            value=None,
            hidden=True,
        )

    def input_widget(self, requirement_name: str):

        object_requirements = [
            "Parent",
            "Root Joint",
            "Tip Joint",
        ]

        if requirement_name in object_requirements:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):

        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                self.option("Shape").get(),
            )

    def run(self):
        ribbon_setup = self.build_ribbon_from_joint_chain(
            parent=self.input("Parent").get()
        )

        descriptor = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        last_control = ribbon_setup.org.name()
        for driving_transform in ribbon_setup.driving_transforms:
            control = aniseed_toolkit.run(
                "Create Control",
                description=f"{descriptor}",
                location=location,
                parent=last_control,
                shape=self.option("Shape").get(),
                shape_scale=12.5,
                config=self.config,
                match_to=driving_transform.full_name(),
            )
            if self.option("Orient Controls To World").get():
                cmds.xform(
                    control.org,
                    rotation=[0, 0, 0],
                    worldSpace=True,
                )
            cmds.parentConstraint(
                control.ctl,
                driving_transform.full_name(),
                maintainOffset=True,
            )
            last_control = control.ctl

    def user_functions(self) -> typing.Dict[str, callable]:

        menu = dict()

        if not self.input("Root Joint").get():
            menu["Create Joints"] = self.user_func_build_skeleton

            return menu

        guide_data = self.option("GuideData").get()
        if guide_data.get("LinkedGuide"):
            menu["Rebuild Ribbon Mesh"] = self.rebuild_ribbon_mesh
            menu["Remove Guide"] = self.user_func_remove_guide
        else:
            menu["Create Guide"] = self.user_func_create_guide

        return menu

    def rebuild_ribbon_mesh(self):

        guide_data = self.guide_data()

        ribbon_mesh = guide_data.get("RibbonMesh")

        if not ribbon_mesh:
            return

        span_count = len(guide_data.get("control_transforms", [])) + 2
        cmds.rebuildSurface(ribbon_mesh, ch=0, rpo=1, rt=0, end=1, kr=0,
                          kcp=0, kc=1, sv=span_count, su=0, du=1, tol=0.01, fr=0, dir=2)


    def user_func_build_skeleton(self, joint_count=None):

        selection = cmds.ls(sl=True)
        external_parent = mref.get(selection[0]) if selection else None

        # -- Ask the user how many joints they want
        joint_count = joint_count or int(
            qtility.request.text(
                title="Joint Count",
                message="How many joints do you want?"
            ),
        )

        # -- If they did not give a valid joint count then we return
        if not joint_count or joint_count < 2:
            return

        # -- Determine the basic increment
        increment = self.default_length / (joint_count - 1)

        # -- Now we can start building the joints
        joints = []
        parent = external_parent
        for idx in range(joint_count):
            joint = mref.get(
                aniseed_toolkit.run(
                    "Create Joint",
                    description=self.option("Descriptive Prefix").get(),
                    location=self.option("Location").get(),
                    parent=parent.full_name() if parent else None,
                    match_to=parent.full_name() if parent else None,
                    config=self.config
                ),
            )

            if idx != 0:
                joint.attribute("translateY").set(increment)

            joints.append(joint)
            parent = joint

        # -- Parent our first joint
        joints[0].set_parent(external_parent)

        # -- Update our inputs
        self.input("Root Joint").set(joints[0].name())
        self.input("Tip Joint").set(joints[-1].name())

        # -- Now we build a guide over this.
        self.user_func_create_guide()

    def build_ribbon_from_joint_chain(self, parent=None):

        guide_data = self.guide_data()

        ribbon = None
        if guide_data["SurfaceData"]:
            ribbon = aniseed_toolkit.run("Construct Nurbs Surface", guide_data["SurfaceData"], parent_transform=self.input("Root Joint").get())

        ribbon_setup = aniseed_toolkit.run(
            "Create Ribbon Setup2",
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
            guide_data["control_transforms"],
            parent=parent,
            ribbon=ribbon,
            skin_data=None,
        )

        # -- We need to rename all the objects
        descriptor = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        ribbon_setup.org.rename(
            self.config.generate_name(
                classification=self.config.organisational,
                description=descriptor,
                location=location,
            ),
        )
        ribbon_setup.no_transform_org.rename(
            self.config.generate_name(
                classification=self.config.organisational,
                description=f"{descriptor}_no_transform",
                location=location,
            ),
        )
        ribbon_setup.follicle_org.rename(
            self.config.generate_name(
                classification=self.config.organisational,
                description=f"{descriptor}_follicles",
                location=location,
            ),
        )
        ribbon_setup.ribbon.rename(
            self.config.generate_name(
                classification=self.config.mechanical,
                description=f"{descriptor}_ribbon",
                location=location,
            ),
        )
        for idx in range(len(ribbon_setup.driving_transforms)):
            ribbon_setup.driving_transforms[idx].rename(
                self.config.generate_name(
                    classification=self.config.mechanical,
                    description=f"{descriptor}_driving_transform",
                    location=location,
                ),
            )
            ribbon_setup.driving_joints[idx].rename(
                self.config.generate_name(
                    classification=self.config.mechanical,
                    description=f"{descriptor}_driving_joint",
                    location=location,
                )
            )

        for follicle in ribbon_setup.follicles:
            follicle.rename(
                self.config.generate_name(
                    classification=self.config.mechanical,
                    description=f"{descriptor}_follicle",
                    location=location,
                )
            )

        if guide_data.get("SkinData"):
            skin_data = aniseed_toolkit.run(
                "Apply Skin Data",
                mesh=ribbon_setup.ribbon.name(),
                weight_data=guide_data.get("SkinData")
            )

        return ribbon_setup

    def user_func_create_guide(self):

        if self.has_guide():
            return

        # -- Check if the guide already exists first
        guide = self.guide_data().get("LinkedGuide")
        if guide and cmds.objExists(guide):
            return []
        
        ribbon_setup = self.build_ribbon_from_joint_chain()

        last_guide = ribbon_setup.org.name()
        for driving_transform in ribbon_setup.driving_transforms:
            guide = aniseed_toolkit.run(
                "Create Guide",
                joint=driving_transform.name(),
                parent=last_guide,
                position_only=False,
                shape="core_cube",
                scale=3.0,
                link_to=last_guide,
            )
            cmds.parentConstraint(
                guide,
                driving_transform.full_name(),
                maintainOffset=True,
            )
            aniseed_toolkit.run(
                "Tag Node",
                guide,
                "GuideControl",
            )
            last_guide = guide

        guide_data = self.guide_data()
        guide_data["LinkedGuide"] = ribbon_setup.org.name()
        guide_data["RibbonMesh"] = ribbon_setup.ribbon.name()
        self.option("GuideData").set(guide_data)

    def user_func_remove_guide(self):

        if not self.has_guide():
            return

        guide_data = self.guide_data()
        linked_guide = guide_data["LinkedGuide"]

        guide_controls = aniseed_toolkit.run(
            "Find All Children With Tag",
            linked_guide,
            "GuideControl",
        )

        root_joint = self.input("Root Joint").get()
        guide_data["control_transforms"] = []
        for guide_control in guide_controls:
            relative_matrix = aniseed_toolkit.run(
                "Get Relative Matrix",
                guide_control,
                root_joint,
            )
            guide_data["control_transforms"].append(relative_matrix)


        joints = aniseed_toolkit.run(
            "Get Joints Between",
            self.input("Root Joint").get(),
            self.input("Tip Joint").get(),
        )

        transforms = dict()
        for joint in joints:
            transforms[joint] = cmds.xform(joint, q=True, ws=True, m=True)

        # -- Store the skin data
        ribbon_mesh = aniseed_toolkit.run(
            "Find First Child With Tag",
            linked_guide,
            "ribbon",
        )

        skin_data = aniseed_toolkit.run(
            "Read Skin Data",
            mesh=ribbon_mesh,
        )
        guide_data["SkinData"] = skin_data
        guide_data["SurfaceData"] = aniseed_toolkit.run("Serialise Nurbs Surface",
                                                        ribbon_mesh, relative_to=self.input("Root Joint").get())
        guide_data["LinkedGuide"] = None
        self.option("GuideData").set(guide_data)
        cmds.delete(linked_guide)

        for joint in joints:
            cmds.xform(joint, ws=True, m=transforms[joint])


    def guide_data(self):
        guide_data = self.option("GuideData").get()

        if not guide_data:
            guide_data = self.default_guide_data()
            self.option("GuideData").set(guide_data)

        return guide_data

    def default_guide_data(self):

        identity_matrix = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                 0.0, 0.0, 1.0]

        matrices = []

        control_count = self.option("Control Count").get()
        increment = self.default_length / (control_count - 1)
        for i in range(control_count):
            matrix = identity_matrix[:]
            matrix[-3] += increment * i
            matrices.append(matrix)

        return dict(
            control_transforms=matrices,
            SkinData={},
            SurfaceData={},
            LinkedGuide=None,
        )

    def has_guide(self):
        """
        Checks whether this has a valid guide or not
        """
        guide = self.guide_data().get("LinkedGuide")
        if guide and cmds.objExists(guide):
            return True
        return False
