import aniseed_toolkit
import maya.cmds as mc


class CreateAimHierarchy(aniseed_toolkit.Tool):
    identifier = "Create Aim Hierarchy"
    classification = "Rigging"
    categories = [
        "Visibility",
    ]

    def run(self, joints: list[str], constrain: bool = True) -> list[str]:

        controls = []

        for idx, joint in enumerate(joints):
            control = mc.createNode("transform", name=f"Control{idx}")

            mc.xform(
                control,
                worldSpace=True,
                matrix=mc.xform(
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

            constraint_host = mc.createNode(
                "transform",
                name=f"CosntraintHost{idx}",
            )
            mc.parent(
                constraint_host,
                controls[idx],
            )
            mc.xform(
                constraint_host,
                worldSpace=True,
                matrix=mc.xform(
                    controls[idx],
                    query=True,
                    worldSpace=True,
                    matrix=True,
                ),
            )

            if idx == len(controls) - 1:
                break

            control_to_aim_at = controls[idx + 1]

            mc.aimConstraint(
                control_to_aim_at,
                constraint_host,
                aimVector=[1, 0, 0],
                upVector=[0, 1, 0],
                worldUpType="objectrotation",
                worldUpObject=controls[idx],
            )

            if constrain:
                mc.parentConstraint(
                    constraint_host,
                    joints[idx],
                    maintainOffset=True,
                )

            constraint_hosts.append(constraint_host)

        return controls
