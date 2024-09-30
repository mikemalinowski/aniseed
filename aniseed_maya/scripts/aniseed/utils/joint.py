import maya.cmds as mc


# --------------------------------------------------------------------------------------
def create(
        description: str,
        location: str,
        parent: str,
        config: "aniseed.RigConfiguration",
        match_to: str = None,
):

    mc.select(clear=True)

    joint_ = mc.joint()

    joint_ = mc.rename(
        joint_,
        config.generate_name(
            classification=config.joint,
            description=description,
            location=location,
        ),
    )

    if parent:
        mc.parent(
            joint_,
            parent,
        )

    if match_to:
        mc.xform(
            joint_,
            matrix=mc.xform(
                match_to,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

    return joint_
