"""
Guides: lightweight controls which drive joints while laying out a skeleton,
along with guide lines and tween guides.
"""
from maya import cmds

from ..core import maths as _maths
from ..core import naming as _naming
from ..scene import shapes as _shapes
from . import tagging as _tagging


def create(
        joint="",
        parent=None,
        position_only=False,
        shape="core_cube",
        scale=3.0,
        link_to=None,
        constrain=True,
    ) -> str:
    """
    Creates a simple guide control object to transform a joint

    Args:
        joint: The joint to drive with this guide
        parent: The parent of this guide
        position_only: If True, the joint will only be position constrained
            to the guide control
        shape: The shape of the guide control (accessible via
            aniseed_toolkit/_resources/shapes
        scale: The scale of the guide control shape
        link_to: If given, a guide line will be drawn between this node
            and the linked node
        constrain: If True then the constraints will be made between the two

    Returns:
        Name of the guide control node
    """

    # -- Create the guide control
    guide_control = cmds.rename(
        cmds.createNode("transform"),
        _naming.unique("GDE_" + joint),
    )
    _tagging.tag(guide_control, "guide")

    cmds.addAttr(
        guide_control,
        shortName="guideLink",
        attributeType="message",
    )

    cmds.connectAttr(
        f"{joint}.message",
        f"{guide_control}.guideLink",
    )

    _shapes.load_shape(
        guide_control,
        shape,
        color=[
            50,
            255,
            50,
        ],
        scale_by=scale,
    )

    cmds.xform(
        guide_control,
        matrix=cmds.xform(
            joint,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    if position_only:
        cns = cmds.pointConstraint(
            guide_control,
            joint,
            maintainOffset=False,
        )

    else:
        cns = cmds.parentConstraint(
            guide_control,
            joint,
            maintainOffset=False,
        )

    # -- We dont want the joints to snap back
    cmds.setAttr(f"{cns[0]}.enableRestPosition", False)

    if not constrain:
        cmds.delete(cns)

    if parent:
        cmds.parent(
            guide_control,
            parent,
        )

    if link_to:
        link(
            guide_control,
            link_to,
        )

    return guide_control


def link(item_a, item_b):

    cmds.select(clear=True)
    curve = cmds.curve(
        degree=1,
        point=[
            (0, 0, 0),
            (0, 0, 0),
        ],
    )

    cmds.setAttr(
        f"{curve}.inheritsTransform",
        False,
    )

    cmds.parent(
        curve,
        item_a,
    )

    curve_shape = cmds.listRelatives(curve, shapes=True)[0]

    # -- Make the curve unselectable
    cmds.setAttr(
        f"{curve_shape}.template",
        True
    )

    # -- Create the first cluster
    cmds.select("%s.cv[0]" % curve_shape)
    cls_root_handle, cls_root_xfo = cmds.cluster()

    # -- Create the second cluster
    cmds.select("%s.cv[1]" % curve)
    cls_target_handle, cls_target_xfo = cmds.cluster()

    # -- Hide the clusters, as we do not want them
    # -- to be interactable
    cmds.setAttr(
        f"{cls_root_xfo}.visibility",
        False,
    )

    cmds.setAttr(
        f"{cls_target_xfo}.visibility",
        False,
    )

    # -- Ensure they"re both children of the guide
    cmds.parent(
        cls_root_xfo,
        item_a,
    )

    cmds.parent(
        cls_target_xfo,
        item_b,
    )

    cmds.xform(
        cls_root_xfo,
        matrix=cmds.xform(
            item_a,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    cmds.xform(
        cls_target_xfo,
        matrix=cmds.xform(
            item_b,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )


def create_tweens(drive_these, from_this, to_this, parent=None):

    for item_to_drive in drive_these:
        create_tween(item_to_drive, from_this, to_this, parent)


def create_tween(drive_this, from_this, to_this, parent=None):
    """
    Creates a blended constraint
    """
    tween_control = create(
        drive_this,
        parent=parent,
        scale=1.5,
        shape="core_sphere",
        constrain=False,
    )
    # -- We specifically dont constrain in the create function as this
    # -- creates a parent constraint and  for a tween we specifically
    # -- want a position constraint.
    cmds.pointConstraint(tween_control, drive_this)

    total_distance = _maths.distance_between(from_this, to_this)
    delta = _maths.distance_between(drive_this, to_this)
    distance_factor = min(1.0, delta / total_distance)

    cns = cmds.pointConstraint(
        to_this,
        tween_control,
        maintainOffset=False,
    )[0]

    cmds.pointConstraint(
        from_this,
        tween_control,
        maintainOffset=False,
    )

    # -- We dont want the joints to snap back
    cmds.setAttr(f"{cns}.enableRestPosition", False)

    cmds.addAttr(
        tween_control,
        shortName="blend",
        attributeType="float",
        keyable=True,
        defaultValue=distance_factor,
    )

    reverse_node = cmds.createNode("reverse")

    cmds.connectAttr(
        f"{tween_control}.blend",
        f"{reverse_node}.inputX",
    )

    cmds.connectAttr(
        f"{reverse_node}.outputX",
        cns + "." + cmds.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[0],
    )

    cmds.connectAttr(
        f"{tween_control}.blend",
        cns + "." + cmds.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[-1],
    )

    for srt in ["s", "t", "r"]:
        for axis in ["x", "y", "z"]:
            cmds.setAttr(
                f"{tween_control}.{srt}{axis}",
                lock=True,
                keyable=False,
            )
