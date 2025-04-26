import aniseed_toolkit
import maya.cmds as mc



class ReplicateJoint(aniseed_toolkit.Tool):

    identifier = "Replicate Joint"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(
        self,
        joint: str = "",
        parent: str = "",
        link: bool = False,
        copy_local_name: bool = False,
    ):
        """
        Replicates an individual joint and makes it a child of the given
        parent.

        Args:
            joint: Joint to replicate
            parent: Node to parent the new node under
            link: If True then the attributes of the initial joint will be
                used as driving connections to this joint.
            copy_local_name: If true, the joint will be renamed to match
                that of the joint being copied (ignoring namespaces)

        Returns:
              The name of the created joint
        """

        # -- Create the joint
        mc.select(clear=True)
        new_joint = mc.joint()

        if parent:
            mc.parent(
                new_joint,
                parent,
            )

        aniseed_toolkit.run(
            "Copy Joint Attributes",
            from_this=joint,
            to_this=new_joint,
            link=link,
        )

        if copy_local_name:
            new_joint = mc.rename(
                new_joint,
                joint.split(":")[-1],
            )

        return new_joint


class CopyJointAttributes(aniseed_toolkit.Tool):

    identifier = "Copy Joint Attributes"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(
        self,
        from_this: str = "",
        to_this: str = "",
        link: bool = False,
    ) -> None:
        """
        Copies all the transform and joint specific attribute data from the
        first given joint to the second.

        Args:
            from_this: The joint to copy values from
            to_this: The joint to copy values to
            link: If true, instead of setting values, the attributes will be
                connected.

        Returns:
            None
        """
        # -- Attributes to copy
        vector_attrs = [
            'translate',
            'rotate',
            'scale',
            'jointOrient',
            'preferredAngle',
        ]

        # -- Set the specific attributes
        for vector_attr in vector_attrs:
            for axis in ['X', 'Y', 'Z']:

                if link:
                    mc.connectAttr(
                        f"{from_this}.{vector_attr + axis}",
                        f"{to_this}.{vector_attr + axis}",
                        force=True,
                    )

                else:
                    mc.setAttr(
                        f"{to_this}.{vector_attr + axis}",
                        mc.getAttr(
                            f"{from_this}.{vector_attr + axis}",
                        ),
                    )


class GetJointsBetween(aniseed_toolkit.Tool):

    identifier = "Get Joints Between"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(
        self,
        start: str = "",
        end: str = "",
    ) -> list[str]:
        """
        This will return all the joints in between the start and end joints
        including the start and end joints. Only joints that are directly
        in the relationship chain between these joints will be included.

        Args:
            start: The highest level joint to search from
            end: The lowest level joint to search from.

        Return:
            List of joints
        """
        joints = []
        next_joint = end

        # -- Get all the joints that make up part of the continuous hierarchy
        long_name = mc.ls(end, long=True)[0]
        chain = long_name.split("|")
        joints = chain[chain.index(start):]
        return joints


class ReplicateChain(aniseed_toolkit.Tool):

    identifier = 'Replicate Chain'
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(
        self,
        from_this: str = "",
        to_this: str = "",
        parent: str = "",
        world: bool = True,
        replacements: dict = None,
    ) -> list[str]:
        """
        Given a start and end joint, this will replicate the joint chain
        between them exactly - ensuring that all joint attributes are correctly
        replicated.

        Args:
             from_this: Joint from which to start duplicating
             to_this: Joint to which the duplicating should stop. Only joints
                between this and from_this will be replicated.
            parent: The node the replicated chain should be parented under
            world: Whether to apply the first replicated chains transform
                in worldspace, otherwise it will be given the same local space
                attribute data.
            replacements: A dictionary of replacements to apply to the duplicated
                joint names.

        Returns:
            List of new joints
        """
        # -- Define our output joints
        new_joints = list()

        joints_to_trace = aniseed_toolkit.run(
            "Get Joints Between",
            from_this,
            to_this,
        )

        # -- We can now cycle through our trace joints and replicate them
        next_parent = parent

        for joint_to_trace in joints_to_trace:
            new_joint = aniseed_toolkit.run(
                "Replicate Joint",
                joint_to_trace,
                parent=next_parent,
            )

            if replacements:
                for replace_this, with_this in replacements.items():
                    new_name = new_joint.replace(
                        replace_this,
                        with_this,
                    )
                    new_name = mc.rename(
                        new_joint,
                        new_name,
                    )

            # -- The first joint we always have to simply match
            # -- in worldspace if required
            if world and joint_to_trace == joints_to_trace[0]:
                mc.xform(
                    new_joint,
                    matrix=mc.xform(
                        joint_to_trace,
                        query=True,
                        matrix=True,
                        worldSpace=True,
                    ),
                    worldSpace=True,
                )

            # -- Store the new joint
            new_joints.append(new_joint)

            # -- Mark the new joint as being the parent for
            # -- the next
            next_parent = new_joint

        return new_joints


class ReverseChain(aniseed_toolkit.Tool):

    identifier = 'Reverse Chain'
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(self, joints: list[str] = None) -> list[str]:
        """
        Reverses the hierarchy of the joint chain.

        Args:
            joints: List of joints in the chain to reverse

        Returns:
            The joint chain in its new order
        """
        # -- Store the base parent so we can reparent the chain
        # -- back under it
        try:
            base_parent = mc.listRelatives(
                joints[0],
                parent=True,
            )[0]

        except (TypeError, IndexError):
            base_parent = None

        # -- Start by clearing all the hierarchy of the chain
        for joint in joints:
            mc.parent(
                joint,
                world=True,
            )

        # -- Now build up the hierarchy in the reverse order
        for idx in range(len(joints)):
            try:
                mc.parent(
                    joints[idx],
                    joints[idx + 1]
                )

            except IndexError:
                pass

        # -- Finally we need to set the base parent once
        # -- again
        if base_parent:
            mc.parent(
                joints[-1],
                base_parent
            )
        else:
            mc.parent(joints[-1], world=True)

        joints.reverse()

        return joints


class ReplicateEntireChain(aniseed_toolkit.Tool):

    identifier = 'Replicate Entire Chain'
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    def run(
        self,
        joint_root: str = "",
        parent: str = "",
        link: bool = False,
        copy_local_name: bool = False,
    ) -> str:
        """
        Given a starting point, this will replicate (duplicate) the entire
        joint chain. It allows for you to specify the parent for the duplicated
        chain, as well as optionally attribute-link it.

        Args:
            joint_root: The joint from which to duplicate from
            parent: The parent node for the duplicated chain
            link: If true, then the attributes will be linked together
            copy_local_name: If true, then the name of the joint being duplicated
                will be used as the name of the joint being created (minus namespace)

        Returns:
            The newly duplicated root joint
        """
        all_joints = mc.listRelatives(
            joint_root,
            ad=True,
            type="joint",
        )

        all_joints.insert(0, joint_root)

        created_joints = dict()
        new_root_joint = None

        for joint in all_joints:

            replicated = aniseed_toolkit.run(
                "Replicate Joint",
                joint,
                parent=None,
                link=link,
                copy_local_name=copy_local_name,
            )

            created_joints[joint] = replicated

            if not new_root_joint:
                new_root_joint = replicated

        # -- Now setup the hierarchy
        for original_joint, new_joint in created_joints.items():

            if original_joint == joint_root:

                if parent:
                    mc.parent(
                        new_joint,
                        parent,
                    )

            else:
                mc.parent(
                    new_joint,
                    created_joints[mc.listRelatives(original_joint, parent=True)[0]],
                )

        return new_root_joint


class GetChainLength(aniseed_toolkit.Tool):

    identifier = 'Get Chain Length'

    categories = [
        "Joints",
    ]

    def run(self, start: str = "", end: str = "", log_result: bool = True) -> float:
        """
        This will calculate the length of the chain in total.

        Args:
            start: The joint from which to start measuring
            end: The joint to which measuring should end
            log_result: If true, the result should be printed

        Returns:
            The total length of all the bones in the chain
        """
        all_joints = aniseed_toolkit.run(
            "Get Joints Between",
            start,
            end,
        )
        distance = 0

        for idx, joint in enumerate(all_joints):

            if not idx:
                continue

            distance += aniseed_toolkit.run(
                "Distance Between",
                joint,
                all_joints[idx - 1],
            )

        if log_result:
            print(f"Distance between {start} and {end}: {distance}")

        return distance
