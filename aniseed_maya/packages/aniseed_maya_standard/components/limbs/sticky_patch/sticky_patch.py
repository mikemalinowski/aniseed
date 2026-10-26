"""
Provides the "Limb : Sticky Patch" component, which drives a joint from a
control under a follicle on a skinned geometry patch, so the joint moves organically with
the underlying skinning (e.g. pouches or fins). It includes user functions to
create, match and skin the patch surface. The patch must not be skinned to the
joint it drives (or its children), otherwise the rig will cycle.
"""
import os
import re
import logging
import mref
import typing
import aniseed
import aniseed_toolkit

from maya import cmds
from maya import mel
from aniseed_maya_standard.mixins import MirrorMixin

log = logging.getLogger(__name__)


class StickyPatchComponent(aniseed.RigComponent, MirrorMixin):
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
        """
        Declares the parent, geometry patch and joint to drive inputs, the
        naming and joint/patch creation options and the control and follicle
        outputs.
        """
        super().__init__(*args, **kwargs)

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

        self.declare_output(
            name="Follicle",
        )

    def on_enter_stack(self):
        """
        When added to the stack we (optionally) create the joint and the
        patch surface for the user
        """
        creation_option = self.option("Create Joint And Patch")

        if creation_option.get():
            self.user_func_create_skeleton(create_patch=True)

        # -- Now we hide that option
        creation_option.set_hidden(True)

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent()

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Exposes the joint and patch creation and editing tools
        """
        menu = super().user_functions()

        if not self.input("Joint To Drive").get():
            menu["Create Joint"] = self.user_func_create_skeleton

        if not self.input("Geometry Patch").get():
            menu["Create Patch Surface"] = self.user_func_create_patch

        menu["Match Patch Surface to Joint"] = self.user_func_match_patch_surface_to_joint
        menu["Skin Patch To Skeleton"] = self.user_func_skin_patch_to_skeleton
        menu["Select Joint"] = self.user_func_select_joint

        return menu

    def run(self):
        """
        Builds a follicle on the patch surface with a control beneath it
        which drives the joint.
        """
        joint_to_drive = self.input("Joint To Drive").get()

        mref.get(self.input("Geometry Patch").get()).attr("inheritsTransform").set(False)

        # -- Now create the follicle
        follicle = self.create_follicle()
        mref.get(follicle).attr("visibility").set(False)

        # -- Scale constraint the follicle transform so that any rig
        # -- scaling still comes through
        follicle_xform = mref.get(follicle).parent()
        mref.scaleConstraint(
            follicle_xform.parent(),
            follicle_xform,
        )

        control = aniseed_toolkit.rig.control.create(
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            parent=follicle_xform.full_name(),
            shape="core_cube",
            config=self.config,
            match_to=joint_to_drive,
        )

        aniseed_toolkit.scene.constraints.parent_and_scale(control.ctl, joint_to_drive)

        self.output("Control").set(control.ctl)
        self.output("Follicle").set(follicle)

    def input_widget(self, requirement_name: str):
        """
        All our inputs are objects, so we use the object selector
        """
        if requirement_name in ["Parent", "Geometry Patch", "Joint To Drive"]:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        """
        Returns the location selector for the location option
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

    def create_follicle(self, u=0.5, v=0.5, prefix="") -> str:
        """
        Creates a follicle on the patch surface at the given u and v and
        parents it under the component parent.

        Returns:
            The name of the follicle shape. Note that the shape keeps its
            default maya name (only the transform is named).
        """
        follicle = mref.create("follicle")
        follicle_xform = follicle.parent()
        follicle_xform.rename(
            self.config.generate_name(
                classification="foll",
                description=self.option("Descriptive Prefix").get() + prefix + "Follicle",
                location=self.option("Location").get(),
            ),
        )

        patch_shape = mref.get(self.input("Geometry Patch").get()).shapes()[0]

        follicle_xform.set_parent(self.input("Parent").get())

        # -- Hook up the surface and transform inputs
        patch_shape.attr("local").connect(follicle.attr("inputSurface"))
        patch_shape.attr("worldMatrix[0]").connect(follicle.attr("inputWorldMatrix"))

        # -- Have the follicle drive its transform
        follicle.attr("outTranslate").connect(follicle_xform.attr("translate"))
        follicle.attr("outRotate").connect(follicle_xform.attr("rotate"))

        follicle.attr("parameterU").set(u)
        follicle.attr("parameterV").set(v)

        follicle_xform.attr("inheritsTransform").set(False)
        follicle.attr("visibility").set(False)

        return follicle.name()

    def user_func_create_skeleton(self, create_patch=False):
        """
        Creates the joint to drive (under the current selection) and
        optionally the patch surface too.
        """
        joint = aniseed_toolkit.scene.joints.create(
            description=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            config=self.config,
            parent=aniseed_toolkit.core.selection.first_selected(),
            match_to=aniseed_toolkit.core.selection.first_selected(),
        )
        self.input("Joint To Drive").set(joint)

        if create_patch:
            self.user_func_create_patch(joint)

    def user_func_create_patch(self, joint_to_drive=None):
        """
        Creates a nurbs plane to act as the patch surface, matched to
        the joint to drive if there is one.
        """
        patch = mref.nurbsPlane(
            pivot=(0, 0, 0),
            axis=(0, 0, 1),
            width=1,
            lengthRatio=1,
            degree=3,
            patchesU=1,
            patchesV=1,
            constructionHistory=True,
        )[0]

        patch.rename(
            self.config.generate_name(
                classification="mesh",
                description=self.option("Descriptive Prefix").get(),
                location=self.option("Location").get(),
            )
        )

        # -- Clear all history
        mref.delete(patch, constructionHistory=True)

        joint_to_drive = joint_to_drive or self.input("Joint To Drive").get()

        if joint_to_drive:
            patch.match_to(joint_to_drive)

        self.input("Geometry Patch").set(patch.name())

    def suggested_label(self):
        """
        Suggests a label based on the description and location
        """
        description = self.option("Descriptive Prefix").get() + " Patch"
        description = re.sub(
            r"(?<!^)(?=[A-Z])",
            " ",
            description.replace("_", " "),
        ).title()

        # -- Now add the location
        location = self.option("Location").get()
        label = f"{description} {location}"

        # -- Finally, we want to check if there are already components in the rig
        # -- with this label and form an identifier.
        existing_labels = {
            component.label()
            for component in self.rig.components(of_type=self.identifier)
        }
        counter = 1
        while f"{label} {counter:02d}" in existing_labels:
            counter += 1
        return f"{label} {counter:02d}"

    def user_func_match_patch_surface_to_joint(self):
        """
        Matches the patch surface to the joint, providing the patch has
        not yet been skinned.
        """
        patch = self.input("Geometry Patch").get()

        if not patch or not mref.objExists(patch):
            log.warning("No patch surface defined")
            return

        surface_node = mref.get(patch)
        surface_shape = surface_node.shape()

        if not surface_shape:
            log.warning("No shape defined")
            return

        has_skin = mref.listConnections(
            surface_shape,
            source=True,
            type="skinCluster",
        )

        if has_skin:
            log.warning("Cannot match transform when the patch has a skin")
            return

        surface_node.match_to(self.input("Joint To Drive").get())

    def user_func_select_joint(self):
        """
        Selects the joint being driven
        """
        joint = self.input("Joint To Drive").get()
        if joint:
            mref.select(joint)

    def user_func_skin_patch_to_skeleton(self):
        """
        Skins the patch to the whole skeleton, except for the joint being
        driven and its children (which would cause a cycle).
        """
        joint = self.input("Joint To Drive").get()
        surface_node = self.input("Geometry Patch").get()

        if not joint:
            log.warning("No joint defined")
            return

        if not surface_node:
            log.warning("No surface node defined")
            return

        joint = mref.get(joint)

        # -- Find the top most joint in the hierarchy of the joint
        joint_root = None
        for node in list(reversed(joint.all_parents())) + [joint]:
            if node.node_type() == "joint":
                joint_root = node
                break

        if not joint_root:
            log.warning("Could not find root joint")
            return

        joints_to_omit = [joint] + joint.children(recursive=True, node_type="joint")
        nodes_to_skin_to = [joint_root] + joint_root.children(recursive=True)

        mref.skinCluster(
            [
                node.full_name()
                for node in nodes_to_skin_to
                if node not in joints_to_omit
            ],
            surface_node,
            toSelectedBones=True,
        )

    def on_serialise(self) -> dict:
        """
        Stores the patch surface, so it can be recreated if it is missing when
        the rig is loaded (for instance when building a rig from a saved file):
        its name, parent, world matrix, degree and spans, the object space
        position of every cv (undeformed, if the patch is skinned) and its skin
        weights if it has any.
        """
        patch = self.input("Geometry Patch").get()

        if not patch or not mref.objExists(patch):
            return dict()

        shape = self._patch_shape(patch)
        if not shape:
            return dict()

        # -- If the patch is skinned, read the cvs from its undeformed
        # -- (intermediate) shape so we store the rest shape of the surface
        cv_shape = self._patch_shape(patch, intermediate=True) or shape

        cv_count_u, cv_count_v = self._patch_cv_counts(shape)

        patch_data = dict(
            name=mref.get(patch).name(),
            parent=(cmds.listRelatives(patch, parent=True) or [""])[0],
            matrix=cmds.xform(patch, query=True, matrix=True, worldSpace=True),
            degree=[
                cmds.getAttr(f"{shape}.degreeU"),
                cmds.getAttr(f"{shape}.degreeV"),
            ],
            spans=[
                cmds.getAttr(f"{shape}.spansU"),
                cmds.getAttr(f"{shape}.spansV"),
            ],
            cvs=[
                cmds.xform(f"{cv_shape}.cv[{u}][{v}]", query=True, translation=True, objectSpace=True)
                for u in range(cv_count_u)
                for v in range(cv_count_v)
            ],
        )

        if mel.eval(f'findRelatedSkinCluster "{patch}";'):
            patch_data["skin"] = aniseed_toolkit.scene.skin.skin_to_dict(patch)

        return dict(patch=patch_data)

    def on_deserialise(self, additional_data: dict) -> None:
        """
        Recreates the patch surface from the stored data, but only if the patch
        does not exist as a surface. If it does, the scene is the truth and is
        left alone, as the stored data may be older than edits made since it
        was saved.

        The patch transform may exist without its surface shape, for instance
        when the rig's saved hierarchy was restored (which recreates
        transforms but not shapes). In that case the transform is deleted and
        the patch is rebuilt in its place. Any child transforms it had are kept
        and moved under the rebuilt patch.
        """
        patch_data = additional_data.get("patch")

        if not patch_data:
            return

        fallback_parent = ""
        orphaned_children = []

        existing_patch = self.input("Geometry Patch").get()
        if existing_patch and mref.objExists(existing_patch):

            # -- A real surface is in the scene, so leave it alone
            if self._patch_shape(existing_patch):
                return

            # -- Only the transform exists, so replace it. Keep its parent in
            # -- case the stored one no longer exists, and move any child
            # -- transforms out (keeping their world transforms) so they
            # -- survive the delete.
            fallback_parent = (cmds.listRelatives(existing_patch, parent=True) or [""])[0]

            children = cmds.listRelatives(
                existing_patch,
                children=True,
                type=["transform", "joint"],
                fullPath=True,
            ) or []
            if children:
                orphaned_children = cmds.parent(children, world=True)

            cmds.delete(existing_patch)

        degree_u, degree_v = patch_data["degree"]
        if degree_u != degree_v:
            log.warning(
                f"Sticky Patch : {self.label()} patch had degree {degree_u} in u and "
                f"{degree_v} in v, it is recreated with degree {degree_u} in both"
            )

        patch = mref.nurbsPlane(
            pivot=(0, 0, 0),
            axis=(0, 0, 1),
            width=1,
            lengthRatio=1,
            degree=degree_u,
            patchesU=patch_data["spans"][0],
            patchesV=patch_data["spans"][1],
            constructionHistory=True,
        )[0]
        mref.delete(patch, constructionHistory=True)

        # -- Give it the stored name, made unique if that is taken
        name = patch_data["name"]
        candidate = name
        counter = 1
        while mref.objExists(candidate):
            candidate = f"{name}{counter}"
            counter += 1
        patch.rename(candidate)
        patch_name = patch.name()

        parent = patch_data.get("parent")
        if not (parent and mref.objExists(parent)):
            parent = fallback_parent

        if parent and mref.objExists(parent):
            patch_name = cmds.parent(patch_name, parent)[0]

        cmds.xform(patch_name, matrix=patch_data["matrix"], worldSpace=True)

        # -- Return any children the replaced transform had
        if orphaned_children:
            cmds.parent(orphaned_children, patch_name)

        shape = self._patch_shape(patch_name)
        cv_count_u, cv_count_v = self._patch_cv_counts(shape)

        if len(patch_data["cvs"]) == cv_count_u * cv_count_v:
            for index, position in enumerate(patch_data["cvs"]):
                u, v = divmod(index, cv_count_v)
                cmds.xform(f"{shape}.cv[{u}][{v}]", translation=position, objectSpace=True)
        else:
            log.warning(
                f"Sticky Patch : {self.label()} stored {len(patch_data['cvs'])} cvs but the "
                f"recreated patch has {cv_count_u * cv_count_v}, so its cvs are not restored"
            )

        self.input("Geometry Patch").set(patch_name)

        skin_data = patch_data.get("skin")
        if skin_data:
            missing = [
                influence
                for influence in skin_data["influences"]
                if not mref.objExists(influence)
            ]

            if missing:
                log.warning(
                    f"Sticky Patch : {self.label()} patch is not re-skinned, as these "
                    f"influences do not exist: {missing}. Use 'Skin Patch To Skeleton' "
                    f"once they do."
                )
            else:
                aniseed_toolkit.scene.skin.dict_to_skin(patch_name, skin_data)

    @staticmethod
    def _patch_shape(patch: str, intermediate: bool = False) -> str:
        """
        Returns the nurbs surface shape of the patch: the deformed (visible)
        shape, or with intermediate the undeformed shape used by a skin.
        Returns an empty string if there is no such shape.
        """
        for shape in cmds.listRelatives(patch, shapes=True, type="nurbsSurface", fullPath=True) or []:
            if bool(cmds.getAttr(f"{shape}.intermediateObject")) == intermediate:
                return shape
        return ""

    @staticmethod
    def _patch_cv_counts(shape: str) -> tuple:
        """
        Returns the number of cvs in u and v of the given (open) nurbs surface.
        """
        return (
            cmds.getAttr(f"{shape}.spansU") + cmds.getAttr(f"{shape}.degreeU"),
            cmds.getAttr(f"{shape}.spansV") + cmds.getAttr(f"{shape}.degreeV"),
        )

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the joint to drive and the geometry patch. Empty unless both
        are set, so that the mirrored component's items always pair up by position.
        """
        joint = self.input("Joint To Drive").get()
        patch = self.input("Geometry Patch").get()

        if not joint or not patch:
            return []

        return [joint, patch]

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the joint to drive, which is where the mirrored component's
        joint is created. Empty if there is no joint or it has no parent.
        """
        joint = self.input("Joint To Drive").get()
        if not joint or not mref.objExists(joint):
            return ""

        parent = mref.get(joint).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Uses the other side's joint and patch if they already exist (the
        search and replaced names). Otherwise this component creates its own joint
        and patch when it enters the stack, which the mirror then moves into
        place.

        Note that a created patch is a fresh plane, so any shaping or skinning
        of the original patch is not carried over.
        """
        original_nodes = [
            mirrored_from.input("Joint To Drive").get(),
            mirrored_from.input("Geometry Patch").get(),
        ]
        mirrored_nodes = [
            self.input("Joint To Drive").get(),
            self.input("Geometry Patch").get(),
        ]

        # -- Without both a joint and a patch on the original there is nothing
        # -- to mirror onto created nodes, so this component keeps its search and
        # -- replaced inputs as they are
        if not all(original_nodes):
            self.option("Create Joint And Patch").set(False)
            return

        if self.mirror_mixin_counterparts_exist(original_nodes, mirrored_nodes):
            self.option("Create Joint And Patch").set(False)
            return

        self.input("Joint To Drive").set("")
        self.input("Geometry Patch").set("")
        self.option("Create Joint And Patch").set(True)


class AngledStickyPatchComponent(StickyPatchComponent):
    """
    A sticky patch where the control is additionally orientated by aiming
    along the patch surface in both the u and v directions.
    """

    identifier = "Limb : Sticky Patch (Aimed)"

    def run(self):
        """
        Builds the standard sticky patch and then inserts an aim based
        resolver between the follicle and the control.
        """
        super().run()

        descriptive = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        # -- Get the control and follicle
        control = aniseed_toolkit.rig.control.get(self.output("Control").get())
        follicle = self.output("Follicle").get()
        follicle_xform = mref.get(follicle).parent()

        # -- Create an aim upvector
        aim_transform = mref.get(
            aniseed_toolkit.scene.transforms.create(
                classification="mech",
                description=descriptive + "Aim",
                location=location,
                config=self.config,
                parent=follicle,
            )
        )
        aim_transform.attr("visibility").set(False)
        aim_transform.match_to(follicle_xform)
        aim_transform.translateZ.set(10)

        # -- We create two readers, one aiming with a v based upvector
        # -- and one with a u based upvector. This allows us to blend
        # -- for the twist
        readers = []
        for axis, u, v in [("V", 0.5, 1), ("U", 1, 0.5)]:
            reader = mref.get(
                aniseed_toolkit.scene.transforms.create(
                    classification="mech",
                    description=descriptive + f"Reader{axis}",
                    location=location,
                    config=self.config,
                    parent=follicle_xform.full_name(),
                )
            )
            reader.match_to(follicle_xform)

            upvector_follicle = self.create_follicle(
                u=u, v=v, prefix=f"Upvector{axis}",
            )
            mref.aimConstraint(
                aim_transform,
                reader,
                aimVector=[0, 0, 1],
                upVector=[0, -1, 0],
                worldUpType="object",
                worldUpObject=upvector_follicle,
                maintainOffset=True,
            )
            readers.append(reader)

        # -- Now we create our resolver. This blends the result of the two
        resolver = mref.get(
            aniseed_toolkit.scene.transforms.create(
                classification="mech",
                description=descriptive + "Resolver",
                location=location,
                config=self.config,
                parent=follicle_xform.full_name(),
            )
        )
        resolver.match_to(follicle_xform)

        # -- Both readers are targets of the same parent constraint
        for reader in readers:
            constraint = mref.parentConstraint(
                reader,
                resolver,
                maintainOffset=False,
            )[0]
        constraint.attr("interpType").set(2)  # -- Shortest

        mref.get(control.org).set_parent(resolver)
