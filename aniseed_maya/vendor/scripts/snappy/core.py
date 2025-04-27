import maya.cmds as mc
import maya.api.OpenMaya as om


# --------------------------------------------------------------------------------------
def new(node, target, group=""):
    """
    Creates a snap mapping from the given node to the target. The current
    offset between the two are stored during this process, allowing for that
    offset to be retained when a snap is requested.

    :param node: The node which can be snapped
    :type node: pm.nt.Transform

    :param target: The node which acts as a snapping target
    :type target: pm.nt.Transform

    :param group: An identifier for the snap offset
    :type group: str

    :return: Snap node containing the offset
    :rtype: pm.nt.DependNode
    """
    # -- Create a new snap node
    snap_node = _create_snap_node()

    # -- Now we can start hooking up the relevant
    # -- attributes
    mc.setAttr(f"{snap_node}.group", group, type="string")
    mc.setAttr(f"{snap_node}.snapNode", True)

    # -- Connect the relationship attributes
    if target:
        mc.connectAttr(
            f"{target}.message",
            f"{snap_node}.snapTarget",
            force=True,
        )

    mc.connectAttr(
        f"{node}.message",
        f"{snap_node}.snapSource",
        force=True,
    )

    if target:
        # -- Finally we need to get the relative matrix
        # -- between the two objects in their current
        # -- state.
        node_to_modify_mat4 = om.MMatrix(
            mc.xform(
                node,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
        )

        node_of_interest_mat4 = om.MMatrix(
            mc.xform(
                target,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
        )

        # -- Determine the offset between the two
        offset_mat4 = node_to_modify_mat4 * node_of_interest_mat4.inverse()

    else:
        offset_mat4 = om.MMatrix()

    # -- Store that matrix into the matrix
    # -- attribute
    mc.setAttr(
        f"{snap_node}.offsetMatrix",
        offset_mat4,
        type="matrix",
    )

    return snap_node


# --------------------------------------------------------------------------------------
def remove(node, group=None):
    """
    Removes any snap relationships on the given node. If a group
    is given then only relationships with that group will be
    removed.

    :param node: The node in which the snap relationships should
        be removed.
    :type node: pm.nt.Transform

    :param group: An optional argument to specify which snap relationship
        should be removed during this call.
    :type group: str

    :return: The number of snap relationships removed.
    """
    snap_nodes = get(node)

    if not snap_nodes:
        return 0

    # -- Assume we need to delete everything
    to_delete = snap_nodes

    # -- Check if we need to filter by a specified lable
    if group:
        to_delete = [
            snap_node 
            for snap_node in snap_nodes 
            if mc.getAttr(f"{snap_node}.group") == group
        ]

    # -- Remove the relationships
    delete_count = len(to_delete)
    mc.delete(to_delete)

    return delete_count


# --------------------------------------------------------------------------------------
def groups(node=None):
    """
    Gives access to all the groups assigned to the given node.

    :param node: Node to query
    :type node: pm.nt.Transform

    :return: list(str, str, str, ...)
    """
    if not node:
        snap_nodes = [
            node.split(".")[0]
            for node in mc.ls("*.snapNode", recursive=True) or list()
        ]

    else:
        snap_nodes = [get(node)]

    found_groups = [
        mc.getAttr(f"{snap_node}.group")
        for snap_node in snap_nodes
    ]

    return list(set(found_groups))


# --------------------------------------------------------------------------------------
def members(group, namespace=None, from_nodes=None):
    """
    This function allows you to query all the nodes which contain
    relationships with a specified group.

    :param group: The group to query for
    :type group: str

    :param namespace: Optional argument to filter only nodes within a given
        namespace
    :type namespace: str

    :param from_nodes: An optional argument to filter only nodes within
        a specific node list
    :type from_nodes: list(pm.nt.Transform, ..)

    :return: list(pm.nt.Transform, pm.nt.Transform, ...)
    """
    # -- Get all the snap nodes
    snap_nodes = mc.ls("*.snapNode", r=True, o=True)

    # -- Define our output
    matched = list()

    for snap_node in snap_nodes:
        # -- Skip nodes which do not have matching groups
        if mc.getAttr(f"{snap_node}.group") != group:
            continue

        # -- Filter any namespace differences if required
        if namespace and namespace not in snap_node:
            continue

        # -- Filter by the node list if given
        if from_nodes:
            source_node = mc.listConnections(
                "L_toeTwist00.translateX",
                source=True,
            )

            if not source_node:
                continue

            if source_node[0] not in from_nodes:
                continue

        matched.append(
            snap_node,
        )
    print(matched)

    return sorted(matched, key=lambda x: mc.ls(mc.listConnections(f"{x}.snapSource", source=True)[0], long=True)[0].count("|"))


def get_node_to_snap_to(node, group):
    """
    Gets the target for the node and group

    :param node: Node to query
    :type node: pm.nt.Transform
    :param group: The group to query for
    :type group: str
    """
    snap_node = get(node=node, group=group)[0]
    target = mc.ls(mc.listConnections(f"{snap_node}.snapTarget", source=True))

    try:
        return target[0]

    except IndexError:
        return None


def get_node_to_snap(node: str, group: str) -> str:
    snap_node = get(node=node, group=group)[0]
    source = mc.ls(mc.listConnections(f"{snap_node}.snapSource", source=True))

    try:
        return source[0]

    except IndexError:
        return None


# --------------------------------------------------------------------------------------
def get(node, target=None, group=None) -> list[str]:
    """
    Returns the snap nodes assigned to the given node

    :param node: Node to query
    :type node: pm.nt.Transform

    :param target: If given, only snap nodes which bind the node and the
        target together are returned.
    :type target: pm.nt.Transform

    :param group: If given only relationships with the given group
        will be returned
    :type group: str

    :return: list(pm.nt.Network, ...)
    """

    if mc.objExists(f"{node}.snapNode"):
        return [node]

    # -- Cycle over all the network nodes connected
    # -- to our snapSource
    possibilities = [
        attr.split(".")[0]
        for attr in mc.listConnections(f"{node}.message", type="network", plugs=True)
        if attr.split(".")[-1] == "snapSource"
    ]

    # -- Ensure we"re only dealing with snap nodes
    possibilities = [
        possibility
        for possibility in possibilities
        if mc.objExists(f"{possibility}.snapNode")
    ]

    # -- If we"re asked to get by group lets restrict
    # -- to that now
    if group:
        possibilities = [
            possibility
            for possibility in possibilities
            if mc.getAttr(f"{possibility}.group") == group
        ]

    # -- If we"re given a specific target lets filter
    # -- out anything else
    if target:
        possibilities = [
            possibility
            for possibility in possibilities
            if target in mc.ls(mc.listConnections(f"{possibility}.snapTarget", source=True))
        ]

    return possibilities


# --------------------------------------------------------------------------------------
def snappable(node):
    """
    Returns True if the given node has any snap nodes linked to it

    :param node: The node to check
    :type node: pm.nt.Transform

    :return: bool
    """
    return len(get(node)) > 0


def update_offset(node, target):

    snap_nodes = get(node, target=target)

    for snap_node in snap_nodes:
        # -- Finally we need to get the relative matrix
        # -- between the two objects in their current
        # -- state.
        node_to_modify_mat4 = om.MMatrix(
            mc.xform(
                node,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
        )

        node_of_interest_mat4 = om.MMatrix(
            mc.xform(
                target,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
        )

        # -- Determine the offset between the two
        offset_mat4 = node_to_modify_mat4 * node_of_interest_mat4.inverse()

        # -- Store that matrix into the matrix
        # -- attribute
        mc.setAttr(
            f"{snap_node}.offsetMatrix",
            offset_mat4,
            type="matrix",
        )


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
def snap(group=None, restrict_to=None, start_time=None, end_time=None, key=True):
    """
    This will match all the members of the snap group.

    :param group: The name of the snap group to get the members from
    :type group: str

    :param restrict_to: If given, only group members which are also present
        within this list will be matched.
    :type restrict_to: pm.nt.Transform

    :param start_time: The time to start from. If this is not given then
        the match will only occur on the current frame
    :type start_time: int

    :param end_time: The time to stop at. If this is not given then the
        match will only occur on the current frame
    :type end_time: int

    :param key: If true the matching will be keyed. Note, if a start and
        end time are given then this is ignored and the motion will always
        be keyed.
    :type key: bool

    :return:
    """
    # -- Get a list of all the snap nodes with this group
    snap_nodes = members(group, from_nodes=restrict_to)

    # -- Use the current time if we"re not given specific
    # -- frame ranges
    start_time = start_time if start_time is not None else int(mc.currentTime(q=True))
    end_time = end_time if end_time is not None else int(mc.currentTime(q=True))

    # -- Log some information, which is useful to know
    print("Snap Nodes : %s" % snap_nodes)
    print("start time : %s" % start_time)
    print("end time : %s" % end_time)

    # -- Cycle the frame range ensuring we dont accidentally
    # -- drop off the last frame
    for frame in range(start_time, end_time + 1):
        mc.currentTime(frame)

        snap_target_matrices = dict()

        for snap_node in snap_nodes:
            target = get_node_to_snap_to(snap_node, group)

            if target:

                # -- Apply the offset
                target_matrix = om.MMatrix(
                    mc.xform(
                        target,
                        q=True,
                        matrix=True,
                        worldSpace=True,
                    ),
                )
                offset_matrix = om.MMatrix(mc.getAttr(f"{snap_node}.offsetMatrix"))
                target_matrix = offset_matrix * target_matrix

                snap_target_matrices[snap_node] = target_matrix

        # for idx in range(len(snap_nodes)):
        for snap_node in snap_nodes:

            node = get_node_to_snap(snap_node, group)

            if not node:
                continue

            # -- Match the two objects with the offset matrix
            if snap_node in snap_target_matrices:
                mc.xform(
                    node,
                    matrix=snap_target_matrices[snap_node],
                    worldSpace=True,
                )

            else:
                _zero_node(node)

            # -- Key the match if we need to
            if key or start_time != end_time:
                mc.setKeyframe(node)


# --------------------------------------------------------------------------------------
def _create_snap_node():
    """
    Snap relationships are stored on network nodes with a very specific
    attribute setup. This function creates that setup for us.

    :return: pm.nt.Network
    """
    snap_node = mc.createNode("network")

    # -- Add an attribute to ensure we can always identify
    # -- this node
    mc.addAttr(
        snap_node,
        longName="snapNode",
        at="bool",
        dv=True,
    )

    mc.addAttr(
        snap_node,
        longName="group",
        dt="string",
    )

    # -- Next add the relationship attributes
    mc.addAttr(
        snap_node,
        longName="snapTarget",
        at="message",
    )

    mc.addAttr(
        snap_node,
        longName="snapSource",
        at="message",
    )

    # -- We add our attributes for offset data
    mc.addAttr(
        snap_node,
        longName="offsetMatrix",
        dt="matrix",
    )

    return snap_node


# --------------------------------------------------------------------------------------
def _set_worldspace_matrix(node, target, offset_matrix):
    """
    Sets the worldspace matrix of the given node to that of the target
    matrix with the offset matrix applied.

    :param node: Node to set the transform on
    :type node: pm.nt.Transform

    :param offset_matrix: The matrix to offset during the apply
    :type offset_matrix: pm.dt.Matrix

    :return: None
    """
    # -- Apply the offset
    target_matrix = om.MMatrix(
        mc.xform(
            target,
            q=True,
            matrix=True,
            worldSpace=True,
        ),
    )
    resolved_mat4 = offset_matrix * target_matrix

    # -- Now we need to apply the matrix
    mc.xform(
        node,
        matrix=resolved_mat4,
        worldSpace=True,
    )

# --------------------------------------------------------------------------------------
def _zero_node(node):
    """
    Zero"s the nodes

    :param node:
    :return:
    """
    for attr_name in mc.listAttr(node, k=True) or list():

        if "scale" in attr_name:
            value = 1.0

        elif "translate" in attr_name or "rotate" in attr_name:
            value = 0.0

        else:
            continue

        try:
            mc.setAttr(f"{node}.{attr_name}", value)
        except RuntimeError:
            pass

    for attr_name in mc.listAttr(node, k=True, ud=True) or list():
        value = mc.attributeQuery(
            attr_name,
            node=node,
            listDefault=True,
        )

        try:
            mc.setAttr(f"{node}.{attr_name}", value)

        except RuntimeError:
            continue