import maya.cmds as mc


# --------------------------------------------------------------------------------------
def hide(items):

    if not isinstance(items, list):
        items = [items]

    for item in items:

        if  mc.nodeType(item, "joint"):
            mc.setAttr(
                f"{item}.drawStyle",
                2,  # Invisible
            )

        else:
            mc.setAttr(
                f"{item}.visibility",
                False,
            )

# --------------------------------------------------------------------------------------
def show(items):

    if not isinstance(items, list):
        items = [items]

    for item in items:

        if mc.nodeType(item, "joint"):
            mc.setAttr(
                f"{item}.drawStyle",
                0,  # Bone
            )

        else:
            mc.setAttr(
                f"{item}.visibility",
                True,
            )
