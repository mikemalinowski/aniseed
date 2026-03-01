import aniseed
import aniseed_toolkit
import maya.cmds as mc



class ReplicateJoint(aniseed_toolkit.Tool):

    identifier = "Replicate Joint"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["joint", "parent"]:
            return aniseed.widgets.ObjectSelector()

    def run(
        self,
        joint: str = "",
        parent: str = "",
        worldspace: bool = False,
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
        return aniseed_toolkit.joints.replicate(
            joint=joint,
            parent=parent,
            worldspace=worldspace,
            link=link,
            copy_local_name=copy_local_name,
        )


class CopyJointAttributes(aniseed_toolkit.Tool):

    identifier = "Copy Joint Attributes"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["from_this", "to_this"]:
            return aniseed.widgets.ObjectSelector()

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
        return aniseed_toolkit.joints.copy_attributes(
            from_this=from_this,
            to_this=to_this,
            link=link,
        )


class GetJointsBetween(aniseed_toolkit.Tool):

    identifier = "Get Joints Between"
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["start", "end"]:
            return aniseed.widgets.ObjectSelector()

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
        return aniseed_toolkit.joints.get_between(start, end)


class ReplicateChain(aniseed_toolkit.Tool):

    identifier = 'Replicate Chain'
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["from_this", "to_this", "parent"]:
            return aniseed.widgets.ObjectSelector()

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
        return aniseed_toolkit.joints.replicate_chain(
            from_this=from_this,
            to_this=to_this,
            parent=parent,
            world=world,
            replacements=replacements,
        )


class ReverseChain(aniseed_toolkit.Tool):

    identifier = 'Reverse Chain'
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name == "joints":
            return aniseed.widgets.ObjectList()

    def run(self, joints: list[str] = None) -> list[str]:
        """
        Reverses the hierarchy of the joint chain.

        Args:
            joints: List of joints in the chain to reverse

        Returns:
            The joint chain in its new order
        """
        return aniseed_toolkit.joints.reverse_chain(joints)


class ReplicateEntireChain(aniseed_toolkit.Tool):

    identifier = 'Replicate Entire Chain'
    classification = "Rigging"
    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["joint_root", "parent"]:
            return aniseed.widgets.ObjectSelector()

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
        return aniseed_toolkit.joints.replicate_entire_chain(
            joint_root=joint_root,
            parent=parent,
            link=link,
            copy_local_name=copy_local_name,
        )


class GetChainLength(aniseed_toolkit.Tool):

    identifier = 'Get Chain Length'

    categories = [
        "Joints",
    ]

    @classmethod
    def ui_elements(cls, keyword_name):
        if keyword_name in ["start", "end"]:
            return aniseed.widgets.ObjectSelector()

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
        return aniseed_toolkit.joints.chain_length(
            start=start,
            end=end,
            log_result=log_result,
        )