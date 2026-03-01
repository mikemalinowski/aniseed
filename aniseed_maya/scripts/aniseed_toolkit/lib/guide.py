import mref
import aniseed_toolkit
from maya import cmds

from . import joints
from . import tagging
from . import naming


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
        naming.unique("GDE_" + joint),
    )
    tagging.tag(guide_control, "guide")

    cmds.addAttr(
        guide_control,
        shortName="guideLink",
        attributeType="message",
    )

    cmds.connectAttr(
        f"{joint}.message",
        f"{guide_control}.guideLink",
    )

    aniseed_toolkit.run("Apply Shape",
        node=guide_control,
        data=shape,
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

    total_distance = aniseed_toolkit.run("Distance Between",
        from_this,
        to_this,
    )

    delta = aniseed_toolkit.run(
        "Distance Between",
        drive_this,
        to_this,
    )
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


def create_ik_guide(start, end, parent=None, constrain_end_orientation=False, link_to=None):
    """
    This will create a 3 bone ik plane guided setup
    """
    # -- Create the org
    org = mref.create("transform", name="ik_org", parent=parent)

    skeletal_joints = joints.get_between(start, end)

    # -- Trace the joints so we can create an ik setup
    ik_joints = [mref.get(j) for j in joints.replicate_chain(start, end)]
    ik_joints[0].set_parent(org)

    # -- Hide these joints
    for ik_joint in ik_joints:
        ik_joint.attr("drawStyle").set(2)  # -- Hidden

    # -- Align our ik joints specifically
    joints.move_rotations_to_orients(joints=[j.full_name() for j in ik_joints])
    cmds.joint(
        ik_joints[0].full_name(),
        edit=True,
        orientJoint="xyz",
        secondaryAxisOrient="ydown",
        children=True,
        zeroScaleOrient=True,
    )

    # -- Create the guides for each joint (so they are correctly placed)
    guides = []
    guide_parent = None
    last_guide = link_to
    for skeletal_joint in skeletal_joints:
        guide = create(
            joint=skeletal_joint,
            parent=guide_parent or org.full_name(),
            position_only=False,
            link_to=last_guide,
            constrain=False,
        )

        # -- This is for our visual linking
        last_guide = guide

        # -- We want the parent of the second two to be the first guide
        if not guide_parent:
            guide_parent = guide

        # -- Store a reference to all the guides
        guides.append(mref.get(guide))

    # -- Determine if we need to lock the end orientation to the guide
    if constrain_end_orientation:
        cmds.parentConstraint(
            guides[-1].full_name(),
            ik_joints[-1].full_name(),
            maintainOffset=True,
            skipTranslate=["x", "y", "z"],
        )

    # -- We now have our guides in the right location for our joints
    # -- so we can setup the ik handle
    ik_handle, _ = cmds.ikHandle(
        startJoint=ik_joints[0].full_name(),
        endEffector=ik_joints[-1].full_name(),
        solver='ikRPsolver',
        priority=1,
    )
    cmds.setAttr(
        f"{ik_handle}.visibility",
        0,
    )

    # -- Make the ik handle follow the last guide
    cmds.parent(
        ik_handle,
        guides[-1].full_name(),
    )

    # -- Make the second guide the upvector - this means it will
    # -- always angle between.
    cmds.poleVectorConstraint(
        guides[1].full_name(),
        ik_handle,
        weight=1,
    )

    # -- Constrain the ik joint root to the first guide
    cns = mref.get(
        cmds.pointConstraint(
            guides[0].full_name(),
            ik_joints[0].full_name(),
        ),
    )
    # -- Now we need to add the stretch in
    upper_distance_node = mref.create("distanceBetween")
    lower_distance_node = mref.create("distanceBetween")

    # -- Distance setup for the upper ik
    guides[0].attr("worldMatrix[0]").connect(upper_distance_node.attr("inMatrix1"))
    guides[1].attr("worldMatrix[0]").connect(upper_distance_node.attr("inMatrix2"))
    upper_distance_node.attr("distance").connect(ik_joints[1].attr("translateX"))

    # -- Distance setup for the lower ik
    guides[1].attr("worldMatrix[0]").connect(lower_distance_node.attr("inMatrix1"))
    guides[2].attr("worldMatrix[0]").connect(lower_distance_node.attr("inMatrix2"))
    lower_distance_node.attr("distance").connect(ik_joints[2].attr("translateX"))

    # -- Now we can constrain the skeletal joints to the
    # -- ik joints. Note that we do this maintaining the offset
    # -- as they may be oriented differently.
    for skeletal_joint, ik_joint in zip(skeletal_joints, ik_joints):
        cns = mref.get(
            cmds.parentConstraint(
                ik_joint.full_name(),
                skeletal_joint,
                maintainOffset=True,
            )[0],
        )

        # -- This flag prevents the joint from moving when its deleted
        cns.attr("enableRestPosition").set(False)

    return org, [guide.full_name() for guide in guides]


def create_multi(targets, parent, children_of_first=False, fk_children=False):

    # -- Declare our output variable
    guides = []
    for target in targets:

        # -- Determine the parent. By default is the given parent
        guide_parent = parent

        if children_of_first and len(guides):
            guide_parent = guides[0]

        if fk_children and len(guides):
            guide_parent = guides[-1]

        guide = create(
            joint=target,
            parent=guide_parent,
            link_to=guides[-1] if len(guides) else None,
        )
