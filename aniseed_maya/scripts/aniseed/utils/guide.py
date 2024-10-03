import bony
import shapeshift
import maya.cmds as mc


# --------------------------------------------------------------------------------------
def create(joint, parent=None, position_only=False, shape="core_cube", scale=3.0):
    """
    Creates a simple guide control object to transform a joint
    """

    # -- Create the guide control
    guide_control = mc.rename(
        mc.createNode("transform"),
        "GDE_" + joint,
    )

    mc.addAttr(
        guide_control,
        shortName="guideLink",
        at="message",
    )

    mc.connectAttr(
        f"{joint}.message",
        f"{guide_control}.guideLink",
    )

    shapeshift.apply(
        node=guide_control,
        data=shape,
        color=[
            50,
            255,
            50,
        ],
        scale_by=scale,
    )

    mc.xform(
        guide_control,
        matrix=mc.xform(
            joint,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    if position_only:
        mc.pointConstraint(
            guide_control,
            joint,
            maintainOffset=False,
        )

    else:
        mc.parentConstraint(
            guide_control,
            joint,
            maintainOffset=False,
        )

    if parent:
        mc.parent(
            guide_control,
            parent,
        )

    return guide_control


# --------------------------------------------------------------------------------------
def aim(
        aim_this,
        to_this,
        aim_axis: bony.direction.Facing = bony.direction.Facing.PositiveX,
        up_axis: bony.direction.Facing = bony.direction.Facing.PositiveY,
):
    """
    Sets up an aim constraint between the two objects
    """
    aim_cns = mc.aimConstraint(
        to_this,
        aim_this,
        aimVector=bony.direction.axis_vector(aim_axis),
        upVector=bony.direction.axis_vector(up_axis),
        worldUpType="scene",
        maintainOffset=False,
    )


# --------------------------------------------------------------------------------------
def tween(drive_this, from_this, to_this, parent=None, factor=None):
    """
    Creates a blended constraint
    """
    tween_control = create(
        drive_this,
        parent=parent,
        scale=1.5,
        shape="core_sphere",
    )

    total_distance = bony.math.distance_between(
        from_this,
        to_this,
    )

    delta = bony.math.distance_between(
        drive_this,
        to_this,
    )
    distance_factor = min(1.0, delta / total_distance)

    cns = mc.pointConstraint(
        to_this,
        tween_control,
        maintainOffset=False,
    )[0]

    mc.pointConstraint(
        from_this,
        tween_control,
        maintainOffset=False,
    )

    mc.addAttr(
        tween_control,
        shortName="blend",
        at="float",
        k=True,
        dv=distance_factor,
    )

    reverse_node = mc.createNode("reverse")

    mc.connectAttr(
        f"{tween_control}.blend",
        f"{reverse_node}.inputX",
    )

    mc.connectAttr(
        f"{reverse_node}.outputX",
        cns + "." + mc.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[0],
    )

    mc.connectAttr(
        f"{tween_control}.blend",
        cns + "." + mc.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[-1],
    )

    for srt in ["s", "t", "r"]:
        for axis in ["x", "y", "z"]:
            mc.setAttr(
                f"{tween_control}.{srt}{axis}",
                lock=True,
                k=False,
            )
