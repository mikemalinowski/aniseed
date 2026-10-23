"""
Aim hierarchies: a transform per joint where each one holds a constraint host
which aims at the next transform, optionally driving the joints.
"""
from maya import cmds


def create_aim_hierarchy(joints: list[str], constrain: bool = True) -> list[str]:
    """
    Creates a transform (named ControlN) at each of the given joints. Each
    transform gets a child constraint host which aims down x at the next
    transform (using the transform itself as the up object). If constrain is
    True, each joint except the last is parent constrained (maintaining
    offset) to its constraint host.

    Args:
        joints: The joints to build the hierarchy for
        constrain: Whether to constrain the joints to the constraint hosts

    Returns:
        The created transforms, one per joint
    """
    controls = []

    for idx, joint in enumerate(joints):
        control = cmds.createNode("transform", name=f"Control{idx}")

        cmds.xform(
            control,
            worldSpace=True,
            matrix=cmds.xform(
                joint,
                worldSpace=True,
                matrix=True,
                query=True,
            ),
        )

        controls.append(control)

    # -- Now constrain backwards
    constraint_hosts = []

    for idx in range(len(controls)):

        constraint_host = cmds.createNode(
            "transform",
            name=f"CosntraintHost{idx}",
        )
        cmds.parent(
            constraint_host,
            controls[idx],
        )
        cmds.xform(
            constraint_host,
            worldSpace=True,
            matrix=cmds.xform(
                controls[idx],
                query=True,
                worldSpace=True,
                matrix=True,
            ),
        )

        if idx == len(controls) - 1:
            break

        control_to_aim_at = controls[idx + 1]

        cmds.aimConstraint(
            control_to_aim_at,
            constraint_host,
            aimVector=[1, 0, 0],
            upVector=[0, 1, 0],
            worldUpType="objectrotation",
            worldUpObject=controls[idx],
        )

        if constrain:
            cmds.parentConstraint(
                constraint_host,
                joints[idx],
                maintainOffset=True,
            )

        constraint_hosts.append(constraint_host)

    return controls
