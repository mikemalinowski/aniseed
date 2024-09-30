import shapeshift
import maya.cmds as mc


# --------------------------------------------------------------------------------------
def create(joints=None):

    if not joints:
        joints = mc.ls(sl=True)

    for joint in joints:

        if mc.nodeType(joint) != "joint":
            continue

        pin_node = mc.rename(
            mc.createNode("transform"),
            f"PIN_{joint}",
        )

        mc.addAttr(
            pin_node,
            shortName="is_pin",
            at="bool",
            dv=True,
        )

        mc.addAttr(
            pin_node,
            shortName="pin_link",
            at="message",
        )

        pin_offset = mc.rename(
            mc.createNode("transform"),
            f"PINOFFSET_{joint}",
        )

        mc.parent(
            pin_offset,
            pin_node,
        )

        shapeshift.apply(
            pin_node,
            "core_pin",
        )
        shapeshift.scale(
            pin_node,
            mc.getAttr(f"{joint}.radius") * 8,
        )

        shapeshift.apply(
            pin_offset,
            "core_sphere",
        )
        shapeshift.scale(
            pin_offset,
            mc.getAttr(f"{joint}.radius") * 3,
        )

        for node in [pin_node, pin_offset]:
            shapeshift.apply_colour(node, r=1, g=0, b=0)

        mc.xform(
            pin_node,
            matrix=mc.xform(
                joint,
                query=True,
                worldSpace=True,
                matrix=True,
            ),
            worldSpace=True,
        )

        mc.connectAttr(
            f"{joint}.message",
            f"{pin_node}.pin_link",
        )

        mc.parentConstraint(
            pin_offset,
            joint,
            maintainOffset=False,
        )

        mc.scaleConstraint(
            pin_offset,
            joint,
            maintainOffset=False,
        )

        mc.setAttr(
            f"{joint}.displayLocalAxis",
            True,
        )

        mc.select(pin_node)

# --------------------------------------------------------------------------------------
def get_joint(item):

    if mc.nodeType(item) == "joint":
        return item

    if item.startswith("PINOFFSET_"):
        item = mc.listRelatives(item, parent=True)[0]

    for potential_result in mc.listConnections(f"{item}.pin_link") or list():
        if mc.nodeType(potential_result) == "joint":
            return potential_result

    return None


# --------------------------------------------------------------------------------------
def get_pin(item):

    if item.startswith("PIN_"):
        return item

    if mc.nodeType(item) == "joint":
        for item in mc.listConnections(f"{item}.message") or list():
            if item.startswith("PIN_"):
                return item

    if item.startswith("PINOFFSET_"):
        return mc.listRelatives(item, parent=True)[0]

    return None


# --------------------------------------------------------------------------------------
def is_pinned(joint):

    for item in mc.listConnections(f"{joint}.message") or list():
        if item.startswith("PIN_"):
            return True

    return False

# --------------------------------------------------------------------------------------
def remove(items=None):

    if not items:
        items = mc.ls(sl=True)

    for pin_or_joint in items:

        joint = get_joint(pin_or_joint)
        pin = get_pin(pin_or_joint)

        pre_xform = mc.xform(
            joint,
            matrix=True,
            query=True,
        )

        mc.setAttr(
            f"{joint}.displayLocalAxis",
            False,
        )

        mc.delete(pin)

        mc.xform(
            joint,
            matrix=pre_xform,
        )
        #
        # if pin_or_joint.startswith("PIN_"):
        #     mc.setAttr(
        #         f"{pin_or_joint.replace('PIN_', '')}.displayLocalAxis",
        #         False,
        #     )
        #     mc.delete(pin_or_joint)
        #     return
        #
        # if pin_or_joint.startswith("PINOFFSET_"):
        #     mc.setAttr(
        #         f"{pin_or_joint.replace('PINOFFSET_', '')}.displayLocalAxis",
        #         False,
        #     )
        #     mc.delete(
        #         mc.listRelatives(
        #             pin_or_joint,
        #             parent=True,
        #         )[0],
        #     )
        #     return
        #
        # for message_input in mc.listConnections(f"{pin_or_joint}.message"):
        #     mc.setAttr(
        #         f"{pin_or_joint}.displayLocalAxis",
        #         False,
        #     )
        #
        #     if message_input.startswith("PIN_"):
        #         mc.delete(message_input)


# --------------------------------------------------------------------------------------
def remove_all():
    for pin in mc.ls("*.pin_link", r=True, o=True):
        remove([pin])

# --------------------------------------------------------------------------------------
def pin_hierarchy(root=None):

    if not root:
        root = mc.ls(sl=True)[0]

    if not root:
        return

    nodes = [root]

    nodes.extend(
        mc.listRelatives(
            root,
            allDescendents=True,
            type="joint",
        ),
    )

    create(nodes)
