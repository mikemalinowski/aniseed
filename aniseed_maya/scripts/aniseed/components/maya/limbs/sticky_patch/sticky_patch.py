import os
import typing
import aniseed
import aniseed_toolkit

import maya.cmds as mc


class StickyPatchComponent(aniseed.RigComponent):
    """
    The sticky patch is a particularly useful component when wanting to have a joint
    or target move in an organic way based on multiple joints.

    It is particularly good when skinning pouches around a characters waist and you
    want the default movement to follow the underlying skinning. It is also very useful
    when creating joints for things like fins/flippers of animals.

    Note: When you skin the patch geometry you must ensure that you do NOT include
    the joint that the patch is driving (or any children of it). If you do, your
    rig evaulation will result in cycles
    """

    identifier = "Limb : Sticky Patch"
    icon = os.path.join(
        os.path.dirname(__file__),
        "sticky_patch.png",
    )

    def __init__(self, *args, **kwargs):
        super(StickyPatchComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Geometry Patch",
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Joint To Drive",
            value="",
            group="Control Rig",
        )

        self.declare_option(
            name="Descriptive Prefix",
            value="md",
            should_inherit=True,
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="md",
            should_inherit=True,
            group="Naming",
            pre_expose=True,
        )

        self.declare_output(
            name="Pin",
        )

    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Patch Surface": self.create_patch,
            "Match Patch Surface to Joint": self.match_patch_surface_to_joint,
            "Skin Patch To Skeleton": self.skin_patch_to_skeleton,
        }

    def run(self):

        xform = self.input("Geometry Patch").get()

        mc.setAttr(
            f"{xform}.inheritsTransform",
            False
        )
        # -- Re-get the surface, as we're not working with a polyPlane any longer
        # -- but instead a mesh shape
        surface = mc.listRelatives(
            xform,
            shapes=True,
        )[0]

        # -- Now create the follicle
        follicle = self.create_follicle()

        mc.setAttr(
            f"{follicle}.visibility",
            False,
        )

        # -- Get the transform so we can properly bind
        follicle_xfo = mc.listRelatives(follicle, p=True)[0]
        mc.setAttr(
            f"{follicle_xfo}.inheritsTransform",
            False,
        )

        # -- Scale constraint the node so that any rig scaling still comes through
        mc.scaleConstraint(
            mc.listRelatives(follicle_xfo, p=True)[0],
            follicle_xfo,
        )

        control = aniseed_toolkit.run("Create Control",
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=follicle_xfo,
            shape="core_cube",
            config=self.config,
            match_to=follicle_xfo,
        )

        mc.parentConstraint(
            control.ctl,
            self.input("Joint To Drive").get(),
            maintainOffset=True,
        )

        self.output("Pin").set(control)

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Parent", "Geometry Patch", "Joint To Drive"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

    def create_follicle(self):

        follicle = mc.rename(
            mc.createNode('follicle'),
            self.config.generate_name(
                classification="foll",
                description=self.option("Descriptive Prefix").get() + "Follicle",
                location=self.option("Location").get(),
            ),
        )

        patch_xform = self.input("Geometry Patch").get()
        patch_shape = mc.listRelatives(
            patch_xform,
            shapes=True,
        )[0]

        mc.parent(
            follicle,
            self.input("Parent").get(),
        )

        mc.connectAttr(
            f"{patch_shape}.local",
            f"{follicle}.inputSurface",
        )

        # -- Hook up the transform input
        mc.connectAttr(
            f"{patch_shape}.worldMatrix[0]",
            f"{follicle}.inputWorldMatrix",
        )

        follicle_parent = mc.listRelatives(follicle, p=True)[0]

        mc.connectAttr(
            f"{follicle}.outTranslate",
            f"{follicle_parent}.translate",
        )

        mc.connectAttr(
            f"{follicle}.outRotate",
            f"{follicle_parent}.rotate",
        )

        mc.setAttr(
            f"{follicle}.parameterU",
            0.5,
        )

        mc.setAttr(
            f"{follicle}.parameterV",
            0.5,
        )

        return follicle

    def create_patch(self):

        xform, _ = mc.nurbsPlane(
            p=[0, 0, 0],
            ax=[0, 0, 1],
            w=1,
            lr=1,
            d=3,
            u=1,
            v=1,
            ch=1
        )

        # -- Clear all history
        mc.delete(xform, constructionHistory=True)

        joint_to_drive = self.input("Joint To Drive").get()

        if joint_to_drive:
            mc.xform(
                xform,
                matrix=mc.xform(
                    joint_to_drive,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )

        self.input("Geometry Patch").set(
            xform,
        )

    def match_patch_surface_to_joint(self):

        surface_node = self.input("Geometry Patch").get()
        surface_shape = mc.listRelatives(
            surface_node,
            shapes=True,
        )[0]

        if not surface_shape:
            print("No shape defined")
            return

        has_skin = len(
            mc.listConnections(
                surface_shape,
                source=True,
                type="skinCluster",
            ),
        )

        if has_skin:
            print("Cannot match transform when the patch has a skin")
            return

        mc.xform(
            surface_node,
            matrix=mc.xform(
                self.input("Joint To Drive").get(),
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

    def skin_patch_to_skeleton(self):

        joint = self.input("Joint To Drive").get()
        surface_node = self.input("Geometry Patch").get()

        if not joint:
            print("No joint defined")
            return

        if not surface_node:
            print("No surface node defined")
            return

        joint_root = None
        long_name = mc.ls(joint, long=True)[0]

        for parent in long_name.split("|"):
            if parent and mc.nodeType(parent) == "joint":
                joint_root = parent
                break

        if not joint_root:
            print("Could not find root joint")
            return

        joints_to_omit = [joint]
        joints_to_omit.extend(
            mc.listRelatives(
                joint,
                allDescendents=True,
                type="joint",
            ),
        )

        joints_to_skin_to = [joint_root]
        joints_to_skin_to.extend(
            mc.listRelatives(
                parent,
                allDescendents=True,
            ),
        )

        joints_to_skin_to = [
            joint
            for joint in joints_to_skin_to
            if joint not in joints_to_omit
        ]

        mc.skinCluster(
            joints_to_skin_to,
            surface_node,
            toSelectedBones=True,
        )
