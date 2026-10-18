"""
Twist setups: a root and tip control with a number of twist controls between
them, each of which blends between the root and tip and aims at the tip.
"""
import typing

import maya.cmds as mc
import mref

from ..core import maths as _maths
from ..rig import control as _control
from ..scene import shapes as _shapes

if typing.TYPE_CHECKING:
    import aniseed


def create_twist_driver(
        joints: list,
        parent: str,
        root: str,
        tip: str,
        description: str,
        location: str,
        config: "aniseed.RigConfiguration",
        constrain_root: bool = True,
        constrain_tip: bool = True,
        shape_rotation=None,
) -> "TwistSetup":
    """
    Builds a twist setup with one twist per joint between the root and tip
    drivers, and drives each joint with its twist.

    The twist org is parented under the parent and matched to the root
    driver, and the twist tip is placed at the tip driver (keeping the org's
    rotation). The root and tip can optionally be parent constrained to their
    drivers. Each twist's blend factor is set from its joint's distance from
    the root driver relative to the root to tip distance, and the joint is
    parent constrained to its twist.

    Args:
        joints: The joints to drive, one twist is created for each
        parent: The node to parent the twist org under
        root: The node driving the root of the twist
        tip: The node driving the tip of the twist
        description: The description used in the twist node names
        location: The location used in the twist node names
        config: The aniseed.RigConfiguration instance
        constrain_root: If True, the twist root is parent constrained (with
            offset) to the root driver
        constrain_tip: If True, the twist tip is parent constrained (with
            offset) to the tip driver
        shape_rotation: Optional x, y, z rotation applied to the shapes of
            every twist control

    Returns:
        The TwistSetup instance
    """
    twist_builder = create_twist_setup(
        twist_count=len(joints),
        description=description,
        location=location,
        config=config,
    )

    # -- Place the org at the root driver and the tip at the tip
    # -- driver, keeping the tip aligned to the org
    twist_org = mref.get(twist_builder.org())
    twist_org.set_parent(parent)
    twist_org.match_to(root)

    twist_tip = mref.get(twist_builder.tip())
    twist_tip.set_position(
        mref.get(tip).get_position(space="world"),
        space="world",
    )
    twist_tip.set_rotation(
        twist_org.get_rotation(space="world"),
        space="world",
    )

    if constrain_root:
        mref.parentConstraint(
            root,
            twist_builder.root(),
            maintainOffset=True,
        )

    if constrain_tip:
        mref.parentConstraint(
            tip,
            twist_tip,
            maintainOffset=True,
        )

    twist_builder.reset_aim()

    # -- Each twist is blended by its joint's distance along the twist
    total_distance = _maths.distance_between(root, tip)

    for idx, (joint, twist) in enumerate(zip(joints, twist_builder.twists())):

        twist_builder.set_blend_factor(
            idx,
            _maths.distance_between(root, joint) / total_distance,
        )

        mref.parentConstraint(
            twist,
            joint,
            maintainOffset=True,
        )

    if shape_rotation is not None:
        for twist_control in twist_builder.all_controls():
            _shapes.rotate(
                twist_control,
                *shape_rotation,
            )

    return twist_builder


def create_twist_setup(
        twist_count: int = 3,
        description: str = "",
        location: str = "",
        config: "aniseed.RigConfiguration" = None,
) -> "TwistSetup":
    """
    This will create a twister setup - this provides two end points which
    can be accessed via twistSetup.root() and twistSetup.tip(). You can also
    access the root org of the twist setup using twistSetup.org()

    All controls can be accessed via twistSetup.all_controls()

    Args:
        twist_count (int): The number of twists to create
        description (str): The description of the twist - this will be used in
            all the node names
        location: The location tag for the nodes
        config: The aniseed.RigConfiguration instance

    Returns:
        The TwistSetup instance
    """
    twist_instance = TwistSetup(
        twist_count=twist_count,
        description=description,
        location=location,
        config=config,
    )
    twist_instance.build()
    return twist_instance


# --------------------------------------------------------------------------------------
class TwistSetup:
    """
    Builds (via build()) a twist org containing a root and tip control and
    twist_count twist controls. Each twist control is driven by a blend of the
    root and tip matrices, aimed at the tip.

    Args:
        twist_count: The number of twist controls to create
        description: The description used in all the node names
        location: The location tag for the nodes
        config: The aniseed.RigConfiguration instance used for naming
    """

    def __init__(self, twist_count, description, location, config):

        # -- Store our incoming variables
        self._twist_count = twist_count
        self._description = description
        self._location = location
        self._config = config

        # -- Store out outgoing variables
        self._org = None
        self._root = None
        self._root_control = None
        self._tip = None
        self._tip_control = None
        self._twists = list()

    # ----------------------------------------------------------------------------------
    def org(self):
        """
        Returns the org node which everything in the setup lives under
        """
        return self._org

    # ----------------------------------------------------------------------------------
    def root(self):
        """
        Returns the org of the root control
        """
        return self._root_control.org

    # ----------------------------------------------------------------------------------
    def tip(self):
        """
        Returns the org of the tip control
        """
        return self._tip_control.org

    # ----------------------------------------------------------------------------------
    def twists(self):
        """
        Returns the twist controls
        """
        return [
            t["twist"]
            for t in self._twists
        ]

    # ----------------------------------------------------------------------------------
    def all_controls(self):
        """
        Returns the twist controls followed by the root and tip controls
        """
        control_nodes = self.twists()
        control_nodes.append(self._root_control.ctl)
        control_nodes.append(self._tip_control.ctl)

        return control_nodes

    # ----------------------------------------------------------------------------------
    def reset_aim(self):
        """
        Sets the primary input axis of every twist's aim matrix to the
        current direction from the root to the tip.
        """

        vector = _maths.direction_between(
            node_a=self._root,
            node_b=self._tip,
            print_result=True,
        )

        for t in self._twists:
            mc.setAttr(
                f"{t['aim_node']}.primaryInputAxisX",
                vector.x,
            )

            mc.setAttr(
                f"{t['aim_node']}.primaryInputAxisY",
                vector.y,
            )

            mc.setAttr(
                f"{t['aim_node']}.primaryInputAxisZ",
                vector.z,
            )

    # ----------------------------------------------------------------------------------
    def set_blend_factor(self, twist_index, blend_factor):
        """
        Sets how far (0-1) between the root and the tip the twist with the
        given index sits. The value is clamped to 0.001 - 0.9999.
        """
        blend_factor = max(
            0.001,
            min(
                0.9999,
                blend_factor,
            )
        )

        mc.setAttr(
            f"{self._twists[twist_index]['blend_node']}.target[1].weight",
            blend_factor,
        )

    # ----------------------------------------------------------------------------------
    def build(self):
        """
        Creates the nodes of the twist setup
        """

        self._org = mc.rename(
            mc.createNode("transform"),
            self._config.generate_name(
                classification="org",
                description=self._description + "TwistGroup",
                location=self._location,
            ),
        )

        self._root_control = _control.create(
            description=f"{self._description}Root",
            location=self._location,
            parent=self._org,
            shape="core_paddle",
            shape_scale=8.0,
            config=self._config,
        )

        self._tip_control = _control.create(
            description=f"{self._description}Tip",
            location=self._location,
            parent=self._org,
            shape="core_paddle",
            shape_scale=8.0,
            config=self._config,
        )

        self._root = mc.rename(
            mc.createNode("transform"),
            self._config.generate_name(
                classification="mech",
                description=self._description + "Root",
                location=self._location,
            ),
        )
        self._tip = mc.rename(
            mc.createNode("transform"),
            self._config.generate_name(
                classification="mech",
                description=self._description + "Tip",
                location=self._location,
            ),
        )

        mc.parent(
            self._root,
            self._org
        )

        mc.parent(
            self._tip,
            self._org,
        )

        mc.parentConstraint(
            self._root_control.ctl,
            self._root,
        )

        mc.parentConstraint(
            self._tip_control.ctl,
            self._tip,
        )

        for idx in range(self._twist_count):

            blend_factor = max(
                0.001,
                min(
                    0.9999,
                    idx if self._twist_count == 1 else idx / (self._twist_count - 1)
                )
            )

            twist = _control.create(
                description=f"{self._description}Twister",
                location=self._location,
                parent=self._org,
                shape="core_paddle",
                shape_scale=4,
                config=self._config,
            )
            connection_point = twist.zero

            blend_matrix = mc.createNode("blendMatrix")
            final_rotation_blender = mc.createNode("blendColors")

            mc.connectAttr(
                f"{self._root}.matrix",
                f"{blend_matrix}.target[0].targetMatrix",
            )

            mc.connectAttr(
                f"{self._tip}.matrix",
                f"{blend_matrix}.target[1].targetMatrix",
            )

            decompose_matrix = mc.rename(
                mc.createNode("decomposeMatrix"),
            )

            aim_matrix = mc.rename(
                mc.createNode("aimMatrix"),
                "aimMatrix",
            )

            mc.connectAttr(
                f"{blend_matrix}.outputMatrix",
                f"{aim_matrix}.inputMatrix",
            )

            mc.connectAttr(
                f"{self._tip}.matrix",
                f"{aim_matrix}.primary.primaryTargetMatrix",
            )

            mc.connectAttr(
                f"{aim_matrix}.outputMatrix",
                f"{decompose_matrix}.inputMatrix"
            )

            mc.connectAttr(
                f"{decompose_matrix}.outputTranslate",
                f"{connection_point}.translate",
            )

            mc.connectAttr(
                f"{decompose_matrix}.outputRotate",
                f"{connection_point}.rotate",
            )

            #
            #
            # mc.connectAttr(
            #     f"{final_rotation_blender}.output",
            #     f"{connection_point}.rotate",
            # )

            mc.setAttr(
                f"{blend_matrix}.target[1].weight",
                blend_factor,
            )

            self._twists.append(
                dict(
                    twist=twist.ctl,
                    blend_node=blend_matrix,
                    aim_node=aim_matrix,
                )
            )
