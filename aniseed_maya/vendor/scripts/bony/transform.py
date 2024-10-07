import maya.cmds as mc


# --------------------------------------------------------------------------------------
def position_between(node, from_this, to_this, factor):

    cns = mc.pointConstraint(
        to_this,
        node,
        maintainOffset=False,
    )[0]

    mc.pointConstraint(
        from_this,
        node,
        maintainOffset=False,
    )

    mc.setAttr(
        cns + "." + mc.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[0],
        1 - factor
    )

    mc.setAttr(
        cns + "." + mc.pointConstraint(
            cns,
            query=True,
            weightAliasList=True,
        )[-1],
        factor,
    )

    xform = mc.xform(
        node,
        query=True,
        matrix=True,
    )

    mc.delete(cns)

    mc.xform(
        node,
        matrix=xform,
    )


# --------------------------------------------------------------------------------------
def get_matrix_relative_to(node, relative_to):

    parent_buffer = mc.createNode("transform")
    child_buffer = mc.createNode("transform")

    mc.parent(
        child_buffer,
        parent_buffer,
    )

    mc.xform(
        parent_buffer,
        matrix=mc.xform(
            relative_to,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
    )

    mc.xform(
        child_buffer,
        matrix=mc.xform(
            node,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    relative_matrix = mc.xform(
        child_buffer,
        query=True,
        matrix=True,
    )

    mc.delete(parent_buffer)

    return relative_matrix

# --------------------------------------------------------------------------------------
def apply_matrix_relative_to(node, matrix, relative_to):
    parent_buffer = mc.createNode("transform")
    child_buffer = mc.createNode("transform")

    mc.parent(
        child_buffer,
        parent_buffer,
    )

    mc.xform(
        parent_buffer,
        matrix=mc.xform(
            relative_to,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
    )

    mc.xform(
        child_buffer,
        matrix=matrix,
    )

    mc.xform(
        node,
        matrix=mc.xform(
            child_buffer,
            query=True,
            matrix=True,
            worldSpace=True,
        ),
        worldSpace=True,
    )

    mc.delete(parent_buffer)


# --------------------------------------------------------------------------------------
def locator_at_center():

    # -- If nothing selected, do nothing
    if not mc.ls(sl=True):
        return

    # -- Create a temporary cluster, snap position, remove temporary cluster/constraint
    temp_cluster = mc.cluster()
    locator = mc.spaceLocator()
    temp_constraint = mc.pointConstraint(
        temp_cluster[1],
        locator,
        mo=False
    )
    mc.delete(temp_cluster, temp_constraint)



