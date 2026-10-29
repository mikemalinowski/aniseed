"""
Provides the IkfkSpringLimb class, which builds an ik/fk limb for a chain of
any number of joints (three or more), using maya's spring ik solver for the
ik.

The chain between the start and end joint is replicated three times:

    * An fk chain, each joint of which is driven directly by an fk control.
    * An ik chain, solved by a spring ik handle under the ik target control,
      with a pole vector control.
    * A blend chain, constrained between the ik and fk chains and blended by
      the ikfk attribute on the root control (0 is ik, 1 is fk). The joints
      the limb is built from are constrained to it.

The ik controls are visible whilst ikfk is below 0.999 and the fk controls
whilst it is above 0.001. Every other control carries ikfk too, as a proxy of
the root control's.

The spring solver shares the bend between the joints by its springAngleBias
ramp. Rather than that ramp being edited directly, it is given a point for
each joint which bends (all but the start and end joint), placed where the
solver samples it for that joint, and the value of each is driven by a
springBias attribute on the ik target control, named for the number of the
joint it bends (springBias02 bends the second joint).

The structure built is:

    SpringRoot (control, matched to the start joint)
        SpringFk 01 -> ## (controls, each under the previous)
        SpringIkTarget (control)
            SpringIkHandleTransform (matched to the handle)
                SpringIkHandle (spring ik handle, with a zero local transform)
        SpringPoleVector (control)
        SpringFkChain (fk joints)
        SpringIkChain (ik joints)
        SpringBlendChain (blend joints, driving the given joints)
"""
import typing

from maya import cmds
from maya import mel
from maya.api import OpenMaya as om

import mref
import aniseed_utilities as au
from aniseed_standard.rigging import ik as _ik
from aniseed_standard.rigging import ikfk as _ikfk
from aniseed_standard.rigging import blend_chain as _blend_chain

if typing.TYPE_CHECKING:
    import aniseed


class IkfkSpringLimb:
    """
    Builds the ik/fk spring limb between two joints.

    Args:
        start_joint: The first joint of the limb
        end_joint: The last joint of the limb, which must be below the start
            joint with at least one joint between them
        ik_target_transform: Optional node to match the ik target control
            to. If not given, it is matched to the end joint.
        config: The aniseed rig configuration used to name every node
        prefix: Placed in front of the description of every node name
        location: The location token (config.left, config.middle etc)
        parent: Optional node to parent the root control under. If not given
            it is created at the scene root.
        shape_scale: Optional scale for the control shapes. If not given it
            is derived from the length of the chain.
        constrain: If True the joints between the start and end joint are
            constrained to the blend chain

    Usage:
        limb = IkfkSpringLimb(hip, ankle, foot_guide, config=config, prefix="leg", location=config.left)
        limb.build()
    """

    # -- The value of each springBias attribute when created. They are all
    # -- equal, so the bend is shared evenly to begin with.
    DEFAULT_BIAS = 0.5

    # -- The ik controls are visible below the first value and the fk
    # -- controls above the second
    IK_VISIBLE_BELOW = 0.999
    FK_VISIBLE_ABOVE = 0.001

    def __init__(
            self,
            start_joint: str,
            end_joint: str,
            ik_target_transform: str = None,
            config: "aniseed.RigConfiguration" = None,
            prefix: str = "",
            location: str = "",
            parent: str = None,
            shape_scale: float = None,
            constrain: bool = True,
    ):
        start = mref.get(start_joint).full_name()
        end = mref.get(end_joint).full_name()

        if not cmds.ls(end, long=True)[0].startswith(f"{cmds.ls(start, long=True)[0]}|"):
            raise ValueError(f"{end_joint} is not below {start_joint}")

        self.joints = [
            mref.get(joint).full_name()
            for joint in au.scene.joints.get_between(start, end)
        ]
        if len(self.joints) < 3:
            raise ValueError("IkfkSpringLimb needs at least three joints")

        self.ik_target_transform = mref.get(ik_target_transform or end).full_name()
        self.config = config
        self.location = location
        self.parent = parent
        self.constrain = constrain

        # -- "leg" becomes "Leg" so it reads as part of a camel cased description
        self.prefix = prefix[:1].upper() + prefix[1:]

        self.chain_length = sum(
            (self._position(b) - self._position(a)).length()
            for a, b in zip(self.joints, self.joints[1:])
        )
        self.shape_scale = shape_scale or self.chain_length / 10.0

        # -- Populated by build
        self.root_control: au.rig.control.Control = None
        self.fk_controls: list[au.rig.control.Control] = []
        self.ik_target_control: au.rig.control.Control = None
        self.pole_vector_control: au.rig.control.Control = None
        self.ik_handle: str = ""
        self.ik_handle_transform: str = ""
        self.fk_chain: list[str] = []
        self.ik_chain: list[str] = []
        self.blend_chain: list[str] = []

    def build(self) -> "IkfkSpringLimb":
        """
        Creates the whole limb.

        Returns:
            This instance, so the created nodes can be read from it
        """
        # -- Ensure the spring solver exists (there is no mref or cmds
        # -- equivalent of this mel procedure)
        mel.eval("ikSpringSolver()")

        self._create_root()
        self._create_fk()
        self._create_ik()
        self._create_spring_bias()
        self._create_blend()

        # -- Every other control carries the ikfk attribute too, as a proxy
        # -- of the root control's, so the limb can be switched from any of them
        ikfk = f"{self.root_control.ctl}.ikfk"
        for control in self.fk_controls + [self.ik_target_control, self.pole_vector_control]:
            mref.get(control.ctl).add_proxy("ikfk", ikfk)

        _ikfk.create_ikfk_visibility(
            attribute=f"{self.root_control.ctl}.ikfk",
            ik_controls=[self.ik_target_control.ctl, self.pole_vector_control.ctl],
            fk_controls=[control.ctl for control in self.fk_controls],
            ik_threshold=self.IK_VISIBLE_BELOW,
            fk_threshold=self.FK_VISIBLE_ABOVE,
        )

        cmds.select(clear=True)
        return self

    @staticmethod
    def _position(node: str) -> om.MVector:
        return om.MVector(cmds.xform(node, query=True, translation=True, worldSpace=True))

    def _description(self, label: str) -> str:
        """
        Returns the description for the given label with the prefix applied
        """
        return f"{self.prefix}{label}"

    def _name(self, classification: str, label: str) -> str:
        """
        Returns a unique name for the given classification and label
        """
        return self.config.generate_name(
            classification=classification,
            description=self._description(label),
            location=self.location,
        )

    def _create_control(self, label: str, parent: str, shape: str, match_to: str = None, **kwargs):
        return au.rig.control.create(
            description=self._description(label),
            location=self.location,
            parent=parent,
            shape=shape,
            config=self.config,
            match_to=match_to,
            **kwargs
        )

    def _create_org(self, label: str) -> str:
        """
        Creates an org under the root control for one of the chains
        """
        return au.scene.transforms.create(
            classification=self.config.organisational,
            description=self._description(label),
            location=self.location,
            config=self.config,
            parent=self.root_control.ctl,
        )

    def _replicate(self, label: str, parent: str) -> list[str]:
        """
        Replicates the chain under the given parent, naming each joint for
        the label, with its rotations moved to its orients
        """
        return [
            mref.get(joint).full_name()
            for joint in _ik.create_ik_chain(
                from_joint=self.joints[0],
                to_joint=self.joints[-1],
                parent=parent,
                name=lambda _: self._name(self.config.mechanical, label),
            )
        ]

    def _create_root(self):
        """
        Creates the root control, which everything else lives under
        """
        self.root_control = self._create_control(
            "SpringRoot",
            parent=self.parent,
            shape="core_cube",
            match_to=self.joints[0],
            shape_scale=self.shape_scale * 1.5,
        )

    def _create_fk(self):
        """
        Creates the fk chain and an fk control per joint, each under the
        previous one, which drives its joint directly
        """
        self.fk_chain = self._replicate("SpringFkChain", self._create_org("SpringFk"))

        parent = self.root_control.ctl
        for joint in self.fk_chain:
            control = self._create_control(
                "SpringFk",
                parent=parent,
                shape="core_paddle",
                match_to=joint,
                shape_scale=self.shape_scale,
                rotate_shape=[0, 0, 90],
            )

            # -- The control was matched to the joint, so there is no offset
            mref.parentConstraint(control.ctl, joint, maintainOffset=False)

            self.fk_controls.append(control)
            parent = control.ctl

    def _create_ik(self):
        """
        Creates the ik chain, solved by a spring ik handle under the ik target
        control and pole vectored to the pole vector control. The end joint's
        rotation follows the ik target control.
        """
        self.ik_chain = self._replicate("SpringIkChain", self._create_org("SpringIk"))

        self.ik_target_control = self._create_control(
            "SpringIkTarget",
            parent=self.root_control.ctl,
            shape="core_cube",
            match_to=self.ik_target_transform,
            shape_scale=self.shape_scale,
        )

        # -- The handle is parented after the pole vector is read, as the
        # -- pole vector is in the space of the handle's parent
        handle = _ik.create_rp_handle(
            start_joint=self.ik_chain[0],
            end_joint=self.ik_chain[-1],
        )
        handle.rename(self._name("ikh", "SpringIkHandle"))
        self.ik_handle = handle.full_name()

        mref.get("ikSpringSolver").attr("message").connect(f"{self.ik_handle}.ikSolver", force=True)
        mref.ikSpringSolverRestPose(self.ik_handle)
        pole_vector = om.MVector(cmds.getAttr(f"{self.ik_handle}.poleVector")[0])

        # -- The handle sits under a transform matched to it, so its own local
        # -- transform is zero and the transform can be used to move the solve
        self.ik_handle_transform = au.scene.transforms.create(
            classification=self.config.mechanical,
            description=self._description("SpringIkHandleTransform"),
            location=self.location,
            config=self.config,
            parent=self.ik_target_control.ctl,
            match_to=self.ik_handle,
        )
        handle.set_parent(self.ik_handle_transform)
        for attribute in ["translate", "rotate"]:
            handle.attr(attribute).set(0, 0, 0)
        self.ik_handle = handle.full_name()

        self.pole_vector_control = self._create_control(
            "SpringPoleVector",
            parent=self.root_control.ctl,
            shape="core_sphere",
            shape_scale=self.shape_scale * 0.5,
        )
        mref.get(self.pole_vector_control.org).set_position(list(self._pole_vector_position(pole_vector)), space="world")
        mref.poleVectorConstraint(self.pole_vector_control.ctl, self.ik_handle, weight=1)
        au.rig.guide.link(self.pole_vector_control.ctl, self.ik_chain[len(self.ik_chain) // 2])

        mref.orientConstraint(self.ik_target_control.ctl, self.ik_chain[-1], maintainOffset=True)

    def _pole_vector_position(self, pole_vector: om.MVector) -> om.MVector:
        """
        Returns where the pole vector control goes: out from the middle of
        the chain, half the chain's length along the solver's own pole
        vector (taken square to the line from the start to the end joint).
        As it is on the side the solver already bends to, constraining to it
        does not move the chain, even when the chain does not bend one way
        (such as an S shape).
        """
        start = self._position(self.ik_chain[0])
        axis = (self._position(self.ik_chain[-1]) - start).normal()
        middle = self._position(self.ik_chain[len(self.ik_chain) // 2])

        side = (pole_vector - axis * (pole_vector * axis)).normal()
        return start + axis * ((middle - start) * axis) + side * self.chain_length * 0.5

    def _create_spring_bias(self):
        """
        Gives the springAngleBias ramp a linear point per joint which bends
        (every joint but the start and end joint), each driven by a
        springBias attribute on the ik target control named for the number
        of the joint it bends (springBias02 bends the second joint).

        The solver samples the ramp for the bending joints at idx / (joint
        count - 1), from the first bending joint at 0, and does not sample it
        for the start or end joint, so the points are placed there. A three
        joint chain has a single bending joint, so its one attribute has no
        effect (a two bone solve has only one answer).
        """
        ctl = mref.get(self.ik_target_control.ctl)
        count = len(self.ik_chain)
        bending = count - 2

        # -- Maya creates two points, which a three joint chain only needs one of
        for idx in range(bending, cmds.getAttr(f"{self.ik_handle}.springAngleBias", size=True)):
            cmds.setAttr(f"{self.ik_handle}.springAngleBias[{idx}].springAngleBias_Position", lock=False)
            cmds.removeMultiInstance(f"{self.ik_handle}.springAngleBias[{idx}]", b=True)

        for idx in range(bending):
            point = f"{self.ik_handle}.springAngleBias[{idx}]"

            # -- Maya creates its points with their positions locked
            position = mref.get(f"{point}.springAngleBias_Position")
            position.unlock()
            position.set(idx / (count - 1.0))
            mref.get(f"{point}.springAngleBias_Interp").set(1)  # -- Linear

            bias = ctl.add_attribute(
                f"springBias{idx + 2:02d}",
                value=self.DEFAULT_BIAS,
                attribute_type="float",
                keyable=True,
                min=0,
                max=1,
                defaultValue=self.DEFAULT_BIAS,
            )
            bias.connect(f"{point}.springAngleBias_FloatValue")

    def _create_blend(self):
        """
        Creates the blend chain between the ik chain (at 0) and the fk chain
        (at 1), which also adds the ikfk attribute to the root control, and
        constrains the given joints to it
        """
        blend = _blend_chain.create_blend_chain(
            parent=self._create_org("SpringBlend"),
            transforms_a=self.ik_chain,
            transforms_b=self.fk_chain,
            attribute_host=self.root_control.ctl,
            attribute_name="ikfk",
            match_transforms=self.fk_chain,
        )

        for joint in blend.blend_joints:
            joint.rename(self._name(self.config.mechanical, "SpringBlendChain"))
            self.blend_chain.append(joint.full_name())

        if self.constrain:
            for blend_joint, joint in zip(self.blend_chain, self.joints):
                mref.parentConstraint(blend_joint, joint, maintainOffset=True)
