"""
Provides the "Limb : Head" component, which builds a chain of fk neck
controls followed by a head control, each driving its joint, with optional
world alignment. It can generate the neck and head joints from head.json when
added to the stack.
"""
import os
import mref
import aniseed
import aniseed_toolkit
import aniseed_toolkit.ui.dialogs


class HeadComponent(aniseed.RigComponent, aniseed.mixins.MirrorMixin):
    """
    This is a very simple component which includes a single neck bone/control and
    a head bone/control in a linear hierarchy.
    """

    identifier = "Limb : Head"
    icon = os.path.join(
        os.path.dirname(__file__),
        "head.png",
    )

    # -- Set on a twin during a mirror when it should keep the joints it
    # -- was given, rather than creating its own
    _mirror_keep_joints = False

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, neck joints and head joint inputs, the prefix,
        location and world alignment options, and the neck and head control
        outputs (the head being the default).
        """
        super(HeadComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Neck Joints",
            value="",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Head Joint",
            value="",
            validate=True,
            group="Required Joints"
        )

        self.declare_option(
            name="Description Prefix",
            value="",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Align Head To World",
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Align Neck To World",
            value=True,
            group="Behaviour",
        )

        self.declare_output(
            "Neck Control",
        )

        self.declare_output(
            "Head Control",
            is_default=True,
        )

    def on_enter_stack(self):
        """
        Creates the neck and head joints under the current selection and
        attempts to hook the parent input to a "tip" or "chest" output. A
        mirrored twin which keeps the joints it was given creates none.
        """
        if not self._mirror_keep_joints:
            self.user_func_create_skeleton()

        # -- Attempt to auto resolve the parent based on its default output
        self.input("Parent").hook_to_parent(tags=["tip", "chest"])

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the parent and head joint inputs and
        an object list for the neck joints.
        """
        if requirement_name in ["Parent", "Head Joint"]:
            return aniseed.widgets.ObjectSelector(component=self)
        if requirement_name == "Neck Joints":
            return aniseed.widgets.ObjectList()

    def option_widget(self, option_name: str):
        """
        Returns an item selector of the left, middle and right locations for
        the Location option.
        """
        if option_name in ["Location"]:
            return aniseed.widgets.ItemSelector(
                items=[
                    self.config.left,
                    self.config.middle,
                    self.config.right,
                ],
                default_item=self.config.middle,
            )

    def user_functions(self):
        """
        Exposes a "Create Joints" menu entry when no head joint is set.
        """
        menu = super(HeadComponent, self).user_functions()

        if not self.input("Head Joint").get():
            menu["Create Joints"] = self.user_func_create_skeleton

        return menu

    def run(self):
        """
        Builds a chain of fk neck controls (one per neck joint) followed by a
        head control, each driving its joint. The neck control output is the
        first neck control, so at least one neck joint is required.
        """

        prefix = self.option("Description Prefix").get()
        location = self.option("Location").get()

        neck_controls = []
        next_parent = self.input("Parent").get()

        for neck_joint in self.input("Neck Joints").get():
            # -- Create the neck control
            neck_control = aniseed_toolkit.rig.control.create(
                description=f"{prefix}Neck",
                location=location,
                parent=next_parent,
                shape="core_circle",
                config=self.config,
                match_to=neck_joint,
                shape_scale=20.0,
            )

            if self.option("Align Neck To World").get():
                mref.get(neck_control.org).set_rotation([0, 0, 0], space="world")

            # -- Constrain our neck
            aniseed_toolkit.scene.constraints.parent_and_scale(
                neck_control.ctl,
                neck_joint,
            )
            neck_controls.append(neck_control)
            next_parent = neck_control.ctl

        # -- Create the head control
        head_joint = self.input("Head Joint").get()
        head_control = aniseed_toolkit.rig.control.create(
            description=f"{prefix}Head",
            location=location,
            parent=next_parent,
            shape="core_lollipop",
            config=self.config,
            match_to=head_joint,
            shape_scale=30.0,
            rotate_shape=[90, 0, 0],
        )

        if self.option("Align Head To World").get():
            mref.get(head_control.org).set_rotation([0, 0, 0], space="world")

        # -- Constrain the head joint
        aniseed_toolkit.scene.constraints.parent_and_scale(
            head_control.ctl,
            head_joint,
        )

        # -- Set our outputs
        self.output("Head Control").set(head_control.ctl)
        self.output("Neck Control").set(neck_controls[0].ctl)

    def user_func_create_skeleton(self):
        """
        Loads the neck and head joints from head.json under the first selected
        node, renames them using the prefix and location, sets the neck and
        head inputs and snaps the neck to the parent's position.
        """

        parent = aniseed_toolkit.core.selection.first_selected()

        joint_map = aniseed_toolkit.ui.dialogs.load_hierarchy_file(
            root_parent=parent,
            filepath=os.path.join(
                os.path.dirname(__file__),
                "head.json",
            ),
            apply_names=False,
            worldspace_root=True,
        )

        location = self.option("Location").get()
        prefix = self.option("Description Prefix").get()

        neck = mref.get(joint_map["JNT_Neck_01_MD"])
        neck.rename(
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{prefix}Neck",
                location=location
            ),
        )

        head = mref.get(joint_map["JNT_Head_01_MD"])
        head.rename(
            self.config.generate_name(
                classification=self.config.joint,
                description=f"{prefix}Head",
                location=location
            ),
        )
        head.set_rotation([0, 0, 0], space="world")

        self.input("Neck Joints").set([neck.name()])
        self.input("Head Joint").set(head.name())

        if parent:
            aniseed_toolkit.scene.transforms.snap_position(neck.name(), parent)

    def _neck_joints(self) -> list:
        """
        Returns the neck joints as a list, which is empty if there are none.
        """
        neck_joints = self.input("Neck Joints").get() or []
        if isinstance(neck_joints, str):
            neck_joints = [neck_joints]
        return list(neck_joints)

    def can_mirror(self) -> bool:
        """
        As well as being on a side, the joints must have a parent: the twin
        creates its joints under the mirrored parent, and cannot create them
        without one.
        """
        return super().can_mirror() and bool(self.mirror_mixin_parent_item())

    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Returns the head joint followed by the neck joints. The head is
        first because the twin always creates a single neck, so if the
        source has more only the extra necks go unpaired.
        """
        head_joint = self.input("Head Joint").get()
        neck_joints = self._neck_joints()

        if not head_joint and not neck_joints:
            return []

        return [head_joint or ""] + neck_joints

    def mirror_mixin_parent_item(self) -> str:
        """
        Returns the parent of the first neck joint (or of the head joint if
        there are no neck joints), which is where the twin creates its joints.
        """
        neck_joints = self._neck_joints()
        root = neck_joints[0] if neck_joints else self.input("Head Joint").get()

        if not root or not mref.objExists(root):
            return ""

        parent = mref.get(root).parent()
        return parent.name() if parent else ""

    def mirror_mixin_prepare_twin(self, source) -> None:
        """
        If the other side joints already exist the twin uses them. Otherwise
        it creates its own when it enters the stack, which needs a parent.
        """
        if self.mirror_mixin_counterparts_exist(
            source.mirror_mixin_items_to_mirror(),
            self.mirror_mixin_items_to_mirror(),
        ):
            self._mirror_keep_joints = True
            return

        if not source.mirror_mixin_parent_item():
            print(
                f"Mirror : {source.label()} has no parent joint, so "
                f"{self.label()} cannot create its joints"
            )
            self._mirror_keep_joints = True
            return

        if len(source._neck_joints()) > 1:
            print(
                f"Mirror : {source.label()} has {len(source._neck_joints())} neck joints "
                f"but {self.label()} creates one. Only the first neck joint is mirrored."
            )

    def mirror_mixin_post_mirror(self, source) -> None:
        """
        Clears the flag which stops the twin creating joints.
        """
        self._mirror_keep_joints = False
