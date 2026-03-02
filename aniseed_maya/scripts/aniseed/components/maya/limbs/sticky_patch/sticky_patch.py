import os
import typing
import aniseed
import aniseed_toolkit
from maya import cmds



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
            value="Patch",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            value="md",
            should_inherit=True,
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Create Joint And Patch",
            value=True,
            group="Creation",
            pre_expose=True,
        )

        self.declare_output(
            name="Control",
        )

    def on_enter_stack(self):
        creation_option = self.option("Create Joint And Patch")

        if creation_option.get():
            self.user_func_create_skeleton(create_patch=True)

        # -- Now we hide that option
        creation_option.set_hidden(True)

    def user_functions(self) -> typing.Dict[str, callable]:
        menu = super(StickyPatchComponent, self).user_functions()

        if not self.input("Joint To Drive").get():
            menu["Create Joint"] = self.user_func_create_skeleton

        if not self.input("Geometry Patch").get():
            menu["Create Patch Surface"] = self.user_func_create_patch

        menu["Match Patch Surface to Joint"] = self.user_func_match_patch_surface_to_joint
        menu["Skin Patch To Skeleton"] = self.user_func_skin_patch_to_skeleton
        menu["Select Joint"] = self.user_func_select_joint

        return menu

    def run(self):

        xform = self.input("Geometry Patch").get()

        cmds.setAttr(
            f"{xform}.inheritsTransform",
            False
        )
        # -- Re-get the surface, as we're not working with a polyPlane any longer
        # -- but instead a mesh shape
        surface = cmds.listRelatives(
            xform,
            shapes=True,
        )[0]

        # -- Now create the follicle
        follicle = self.create_follicle()

        cmds.setAttr(
            f"{follicle}.visibility",
            False,
        )

        # -- Get the transform so we can properly bind
        follicle_xfo = cmds.listRelatives(follicle, parent=True)[0]
        cmds.setAttr(
            f"{follicle_xfo}.inheritsTransform",
            False,
        )

        # -- Scale constraint the node so that any rig scaling still comes through
        cmds.scaleConstraint(
            cmds.listRelatives(follicle_xfo, parent=True)[0],
            follicle_xfo,
        )

        control = aniseed_toolkit.run("Create Control",
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=follicle_xfo,
            shape="core_cube",
            config=self.config,
            match_to=self.input("Joint To Drive").get(),
        )

        cmds.parentConstraint(
            control.ctl,
            self.input("Joint To Drive").get(),
            maintainOffset=True,
        )

        self.output("Control").set(control.ctl)

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Parent", "Geometry Patch", "Joint To Drive"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

    def create_follicle(self):

        follicle = cmds.rename(
            cmds.createNode('follicle'),
            self.config.generate_name(
                classification="foll",
                description=self.option("Descriptive Prefix").get() + "Follicle",
                location=self.option("Location").get(),
            ),
        )

        patch_xform = self.input("Geometry Patch").get()
        patch_shape = cmds.listRelatives(
            patch_xform,
            shapes=True,
        )[0]

        cmds.parent(
            follicle,
            self.input("Parent").get(),
        )

        cmds.connectAttr(
            f"{patch_shape}.local",
            f"{follicle}.inputSurface",
        )

        # -- Hook up the transform input
        cmds.connectAttr(
            f"{patch_shape}.worldMatrix[0]",
            f"{follicle}.inputWorldMatrix",
        )

        follicle_parent = cmds.listRelatives(follicle, parent=True)[0]

        cmds.connectAttr(
            f"{follicle}.outTranslate",
            f"{follicle_parent}.translate",
        )

        cmds.connectAttr(
            f"{follicle}.outRotate",
            f"{follicle_parent}.rotate",
        )

        cmds.setAttr(
            f"{follicle}.parameterU",
            0.5,
        )

        cmds.setAttr(
            f"{follicle}.parameterV",
            0.5,
        )

        return follicle

    def user_func_create_skeleton(self, create_patch=False):
        joint = aniseed_toolkit.joints.create(
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            config=self.config,
            parent=aniseed_toolkit.mutils.first_selected(),
            match_to=aniseed_toolkit.mutils.first_selected(),
        )
        self.input("Joint To Drive").set(joint)

        if create_patch:
            self.user_func_create_patch(joint)

        # -- Add our joints to a deformers set.
        aniseed_toolkit.sets.add_to(joint, set_name="deformers")

    def user_func_create_patch(self, joint_to_drive=None):

        xform, _ = cmds.nurbsPlane(
            pivot=(0, 0, 0),
            axis=(0, 0, 1),
            width=1,
            lengthRatio=1,
            degree=3,
            patchesU=1,
            patchesV=1,
            constructionHistory=True,
        )

        # -- Clear all history
        cmds.delete(xform, constructionHistory=True)

        joint_to_drive = joint_to_drive or self.input("Joint To Drive").get()

        if joint_to_drive:
            cmds.xform(
                xform,
                matrix=cmds.xform(
                    joint_to_drive,
                    query=True,
                    matrix=True,
                    worldSpace=True,
                ),
                worldSpace=True,
            )
        
            # -- Rename the mesh
            xform = cmds.rename(xform, f"MESH_{xform}")

        self.input("Geometry Patch").set(
            xform,
        )

    def user_func_match_patch_surface_to_joint(self):

        surface_node = self.input("Geometry Patch").get()
        surface_shape = cmds.listRelatives(
            surface_node,
            shapes=True,
        )[0]

        if not surface_shape:
            print("No shape defined")
            return

        has_skin = len(
            cmds.listConnections(
                surface_shape,
                source=True,
                type="skinCluster",
            ) or [],
        )

        if has_skin:
            print("Cannot match transform when the patch has a skin")
            return

        cmds.xform(
            surface_node,
            matrix=cmds.xform(
                self.input("Joint To Drive").get(),
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

    def user_func_select_joint(self):
        joint = self.input("Joint To Drive").get()
        if joint:
            cmds.select(joint)

    def user_func_skin_patch_to_skeleton(self):

        joint = self.input("Joint To Drive").get()
        surface_node = self.input("Geometry Patch").get()

        if not joint:
            print("No joint defined")
            return

        if not surface_node:
            print("No surface node defined")
            return

        joint_root = None
        long_name = cmds.ls(joint, long=True)[0]

        for parent in long_name.split("|"):
            if parent and cmds.nodeType(parent) == "joint":
                joint_root = parent
                break

        if not joint_root:
            print("Could not find root joint")
            return

        joints_to_omit = [joint]
        joints_to_omit.extend(
            cmds.listRelatives(
                joint,
                allDescendents=True,
                type="joint",
            ) or [],
        )

        joints_to_skin_to = [joint_root]
        joints_to_skin_to.extend(
            cmds.listRelatives(
                parent,
                allDescendents=True,
            ),
        )

        joints_to_skin_to = [
            joint
            for joint in joints_to_skin_to
            if joint not in joints_to_omit
        ]

        cmds.skinCluster(
            joints_to_skin_to,
            surface_node,
            toSelectedBones=True,
        )
