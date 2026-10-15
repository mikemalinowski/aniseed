"""
Deprecated guide functions, kept importable until aniseed_toolkit 4.0.

create_ik_guide was unused and create_multi never worked (it never stored the
guides it created and returned None). Access them through
aniseed_toolkit.guide as before - a DeprecationWarning is logged.
"""
import mref
from maya import cmds

from ..lib import joints
from ..lib.guide import create


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
