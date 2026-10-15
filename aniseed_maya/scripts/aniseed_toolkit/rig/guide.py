"""
Guides: lightweight controls which drive joints while laying out a skeleton,
along with guide lines and tween guides.
"""
from maya import cmds
import mref

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
    Creates a simple guide control object to transform a joint. The guide
    is named GDE_<joint> (made unique), tagged as "guide", linked to the
    joint through its guideLink attribute and matched to the joint's world
    transform.

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
        constrain: If True the guide constrains the joint. If False the
            constraint is still created (so node names are unaffected) but
            is then deleted.

    Returns:
        Name of the guide control node
    """

    # -- Create the guide control
    guide_control = mref.create("transform")
    guide_control.rename(_naming.unique("GDE_" + joint))
    _tagging.tag(guide_control.name(), "guide")

    guide_link = guide_control.add_attribute(
        "guideLink",
        value=None,
        attribute_type="message",
    )

    # -- The passthrough (rather than Attribute.connect) is used so that
    # -- a failed connection raises
    mref.connectAttr(
        f"{joint}.message",
        guide_link,
    )

    _shapes.load_shape(
        guide_control.name(),
        shape,
        color=[
            50,
            255,
            50,
        ],
        scale_by=scale,
    )

    guide_control.match_to(joint)

    if position_only:
        cns = mref.pointConstraint(
            guide_control,
            joint,
            maintainOffset=False,
        )

    else:
        cns = mref.parentConstraint(
            guide_control,
            joint,
            maintainOffset=False,
        )

    # -- We dont want the joints to snap back
    cns[0].attr("enableRestPosition").set(False)

    if not constrain:
        mref.delete(cns)

    if parent:
        mref.parent(
            guide_control,
            parent,
        )

    if link_to:
        link(
            guide_control.name(),
            link_to,
        )

    return guide_control.name()


def link(item_a, item_b):
    """
    Draws a guide line (a templated, linear curve) between the two nodes.
    The curve lives under item_a and each end is driven by a hidden
    cluster, one under item_a and one under item_b.

    The selection is changed by this function (the clusters are created
    from component selections).

    Args:
        item_a: The node the line starts from (and which owns the curve)
        item_b: The node the line ends at
    """
    cmds.select(clear=True)
    curve = mref.curve(
        degree=1,
        point=[
            (0, 0, 0),
            (0, 0, 0),
        ],
    )

    curve.attr("inheritsTransform").set(False)

    mref.parent(
        curve,
        item_a,
    )

    curve_shape = curve.shapes()[0]

    # -- Make the curve unselectable
    curve_shape.attr("template").set(True)

    # -- Create the first cluster (cmds.cluster returns the cluster
    # -- deformer followed by its handle transform)
    mref.select(f"{curve_shape.full_name()}.cv[0]")
    _, cls_root_xfo = mref.cluster()

    # -- Create the second cluster
    mref.select(f"{curve.full_name()}.cv[1]")
    _, cls_target_xfo = mref.cluster()

    # -- Hide the clusters, as we do not want them
    # -- to be interactable
    cls_root_xfo.attr("visibility").set(False)
    cls_target_xfo.attr("visibility").set(False)

    # -- Ensure they're both children of the guide
    mref.parent(
        cls_root_xfo,
        item_a,
    )

    mref.parent(
        cls_target_xfo,
        item_b,
    )

    cls_root_xfo.match_to(item_a)
    cls_target_xfo.match_to(item_b)


def create_tweens(drive_these, from_this, to_this, parent=None):
    """
    Creates a tween guide (see create_tween) for each of the given nodes.

    Args:
        drive_these: The nodes (typically joints) to create tween guides for
        from_this: The node the tweens blend from
        to_this: The node the tweens blend to
        parent: Optional parent for the tween guides
    """
    for item_to_drive in drive_these:
        create_tween(item_to_drive, from_this, to_this, parent)


def create_tween(drive_this, from_this, to_this, parent=None):
    """
    Creates a tween guide which position constrains the given node. The
    guide itself is point constrained between from_this and to_this, and
    its "blend" attribute (which defaults to the node's current relative
    distance between the two) sets the weighting. The transform channels
    of the guide are locked.

    Args:
        drive_this: The node (typically a joint) to drive
        from_this: The node the tween blends from
        to_this: The node the tween blends to
        parent: Optional parent for the tween guide
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
    mref.pointConstraint(tween_control, drive_this)

    total_distance = _maths.distance_between(from_this, to_this)
    delta = _maths.distance_between(drive_this, to_this)
    distance_factor = min(1.0, delta / total_distance)

    cns = mref.pointConstraint(
        to_this,
        tween_control,
        maintainOffset=False,
    )[0]

    mref.pointConstraint(
        from_this,
        tween_control,
        maintainOffset=False,
    )

    # -- We dont want the joints to snap back
    cns.attr("enableRestPosition").set(False)

    tween_node = mref.get(tween_control)
    blend = tween_node.add_attribute(
        "blend",
        value=None,
        attribute_type="float",
        keyable=True,
        defaultValue=distance_factor,
    )

    reverse_node = mref.create("reverse")

    mref.connectAttr(
        blend,
        reverse_node.attr("inputX"),
    )

    # -- The first weight is for to_this, the last for from_this
    weights = cns.weight_attributes()

    mref.connectAttr(
        reverse_node.attr("outputX"),
        weights[0],
    )

    mref.connectAttr(
        blend,
        weights[-1],
    )

    # -- The setAttr passthrough is used rather than Attribute.set, as
    # -- Attribute.set queries the attribute type first, which evaluates
    # -- the (constrained) channel and so changes the result of any later
    # -- tween in the same chain.
    for srt in ["s", "t", "r"]:
        for axis in ["x", "y", "z"]:
            mref.setAttr(
                f"{tween_node.full_name()}.{srt}{axis}",
                lock=True,
                keyable=False,
            )
