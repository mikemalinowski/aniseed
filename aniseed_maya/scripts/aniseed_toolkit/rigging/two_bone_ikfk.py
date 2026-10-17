"""
A complete two bone ik/fk setup: an ik chain, an fk chain and a chain which
blends between them, optionally with soft ik.
"""
import mref

from . import blend_chain as _blend_chain
from . import ik as _ik
from ..scene import joints as _joints
from . import soft_ik as _soft_ik


def create_two_bone_ikfk(
        parent,
        root_joint,
        end_joint,
        attribute_host,
        attribute_name,
        soft_ik=None,
        soft_ik_host=None,
        constrain=True,
        constrain_endpoint_rotation=True,
        ik_target_transform_override=None,
    ):
    """
    Creates a TwoBoneIKFK (see TwoBoneIKFK for the arguments) and builds it.

    Returns:
        The TwoBoneIKFK, which gives access to the created nodes
    """
    instance = TwoBoneIKFK(
        parent,
        root_joint,
        end_joint,
        attribute_host,
        attribute_name,
        soft_ik,
        soft_ik_host,
        constrain,
        constrain_endpoint_rotation,
        ik_target_transform_override,
    )
    instance.create()
    return instance


class TwoBoneIKFK:
    """
    Builds an ik chain, an fk chain and a chain which blends between the
    two (driven by the given attribute, where 0 is ik and 1 is fk). The
    blend chain optionally constrains the joints it was built from.

    The ik target, upvector and fk chain are left for the caller to drive.

    The created nodes are named ik, fk, nk, ik_target etc, with a counter
    from 2 when the name is taken (see unique_name).

    Args:
        parent: The node to create the ikfk_org under
        root_joint: The first joint of the chain to build from
        end_joint: The last joint of the chain to build from
        attribute_host: The node to add the blend attribute to
        attribute_name: The name of the blend attribute (0 is ik, 1 is fk)
        soft_ik: If True soft ik is applied to the ik chain
        soft_ik_host: The node to add the soft ik attributes to. A network
            node is created if this is not given.
        constrain: If True the blend chain parent constrains the joints
            between root_joint and end_joint
        constrain_endpoint_rotation: If True the rotation of the last ik
            joint follows the ik target
        ik_target_transform_override: Optional node to place the ik target
            at, rather than the last ik joint
    """

    def __init__(
            self,
            parent,
            root_joint,
            end_joint,
            attribute_host,
            attribute_name,
            soft_ik=None,
            soft_ik_host=None,
            constrain=True,
            constrain_endpoint_rotation=True,
            ik_target_transform_override=None,
    ):
        # -- Store our input variables
        self.parent = mref.get(parent)
        self.root_joint = mref.get(root_joint)
        self.end_joint = mref.get(end_joint)
        self.attribute_host = mref.get(attribute_host)
        self.attribute_name = attribute_name
        self.apply_soft_ik = soft_ik
        self.soft_ik_host = mref.get(soft_ik_host) if soft_ik_host else None
        self.driven_joints = _joints.get_between(
            self.root_joint.full_name(),
            self.end_joint.full_name(),
        )
        self.constrain = constrain
        self.constrain_endpoint_rotation = constrain_endpoint_rotation
        self.ik_target_transform_override = ik_target_transform_override

        # -- Declare our output variables
        self.org = None
        self.ik_chain = None
        self.fk_chain = None
        self.blend_chain = None
        self.ik_target = None
        self.ik_upvector = None
        self.soft_ik_root = None
        self.soft_ik_target = None

    def create(self):
        """
        Builds the setup: the ikfk_org, then the fk chain, the ik chain and
        finally the blend chain.
        """
        self.org = mref.create(
            "transform",
            name="ikfk_org",
            parent=self.parent,
        )
        self.create_fk()
        self.create_ik()
        self.create_blend()

    def create_ik(self):
        """
        Builds the ik chain with a rotate plane ik handle beneath the ik
        target and pole vector constrained to the ik upvector, plus the
        optional endpoint rotation constraint and soft ik.
        """
        # -- Create the ik chain with the rotations moved to the orients
        self.ik_chain = mref.get(
            _ik.create_ik_chain(
                from_joint=self.root_joint.full_name(),
                to_joint=self.end_joint.full_name(),
                parent=self.org.full_name(),
                name=lambda _: unique_name("ik"),
            )
        )

        # -- Create our ik targets
        self.ik_target = mref.create("transform", name=unique_name("ik_target"), parent=self.org)
        self.ik_upvector = mref.create("transform", name=unique_name("ik_upvector"), parent=self.org)

        self.ik_target.match_to(self.ik_target_transform_override or self.ik_chain[-1])
        self.ik_upvector.match_to(self.ik_chain[1])

        # -- Setup the ik
        _ik.create_rp_handle(
            start_joint=self.ik_chain[0].full_name(),
            end_joint=self.ik_chain[-1].full_name(),
            parent=self.ik_target,
            pole_vector=self.ik_upvector,
        )

        # -- Constrain the rotation of the last joint
        if self.constrain_endpoint_rotation:
            mref.parentConstraint(
                self.ik_target,
                self.ik_chain[-1],
                maintainOffset=True,
                skipTranslate=["x", "y", "z"],
            )

        if self.apply_soft_ik:
            self.apply_soft_ik_behaviour()

    def create_fk(self):
        """
        Builds the fk chain, a replica of the joint chain under the org.
        """
        self.fk_chain = mref.get(
            _joints.replicate_chain(
                from_this=self.root_joint.full_name(),
                to_this=self.end_joint.full_name(),
                parent=self.org.full_name(),
            ),
        )
        for joint in self.fk_chain:
            joint.rename(unique_name("fk"))

    def create_blend(self):
        """
        Builds the blend chain between the ik and fk chains (placed at the
        fk chain), and if constrain is True, constrains the driven joints
        to it.
        """
        self.blend_chain = mref.get(
            _blend_chain.create_blend_chain(
                parent=self.org.full_name(),
                transforms_a=self.ik_chain.full_names(),
                transforms_b=self.fk_chain.full_names(),
                attribute_host=self.attribute_host.full_name(),
                attribute_name=self.attribute_name,
                match_transforms=self.fk_chain.full_names(),
            ).blend_joints
        )

        for driven_joint, blend_joint in zip(self.driven_joints, self.blend_chain):
            blend_joint.rename(unique_name("nk"))
            if self.constrain:
                mref.parentConstraint(
                    blend_joint.name(),
                    driven_joint,
                    maintainOffset=True,
                )

    def apply_soft_ik_behaviour(self):
        """
        Creates the soft ik root (under the org, at the first ik joint) and
        target (under the ik target, at the last ik joint) and applies two
        bone soft ik to the ik chain.
        """
        self.soft_ik_root = mref.create(
            "transform",
            name=unique_name("soft_ik_root"),
            parent=self.org.full_name(),
        )
        self.soft_ik_root.match_to(self.ik_chain[0])

        self.soft_ik_target = mref.create(
            "transform",
            name=unique_name("soft_ik_target"),
            parent=self.ik_target.full_name(),
        )
        self.soft_ik_target.match_to(self.ik_chain[-1].full_name())

        # -- Now create the actual soft ik setup
        _soft_ik.create_two_bone_soft_ik(
            root=self.soft_ik_root.full_name(),
            target=self.soft_ik_target.full_name(),
            second_joint=self.ik_chain[-2].full_name(),
            third_joint=self.ik_chain[-1].full_name(),
            host=self.soft_ik_host.full_name() if self.soft_ik_host else None,
        )

    def unique_name(self, name):
        """
        Same as the module level unique_name.
        """
        return unique_name(name)

    def all_nodes(self):
        """
        Returns the ik target, ik upvector and the joints of the fk, ik and
        blend chains.
        """
        return [
            self.ik_target,
            self.ik_upvector
        ] + self.fk_chain + self.ik_chain + self.blend_chain


def unique_name(name: str) -> str:
    """
    Returns the given name, or if it is already in use, the name with the
    lowest available counter suffix - starting from 2.
    """
    counter = 1
    proposed_name = name

    while mref.objExists(proposed_name):
        counter += 1
        proposed_name = f"{name}{counter}"

    return proposed_name
