"""
Provides the "Dev Example : Joint Chain (cmds)" component, which creates an
evenly spaced joint chain between two nodes, using only maya.cmds.

What this example teaches:
    * A "creator": a component which builds new nodes
    * Declaring outputs, and filling them in during run
    * Naming nodes through the rig configuration
    * Using aniseed's location, number and object widgets

Compare with: ex08_joint_chain_openmaya.py, which does exactly the same job,
with the same inputs, options and outputs, using OpenMaya.

Read next: ex08_joint_chain_openmaya.py
"""
import logging

# -- maya.cmds is the only Maya API this example uses
from maya import cmds

import aniseed

log = logging.getLogger(__name__)


class JointChainCmds(aniseed.RigComponent):
    """
    Creates a chain of joints spaced evenly from the Start node to the End
    node. Each joint's X axis aims down the chain, with Y pointing up.
    """

    identifier = "Dev Example : Joint Chain (cmds)"

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent, Start and End inputs, the naming and joint count
        options, and the Root Joint, Tip Joint and Joints outputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the chain is parented under. If empty, the chain is left in the world.",
            # -- This input is optional, so it should not stop the build
            # -- when it is empty
            validate=False,
            group="Scene",
        )

        self.declare_input(
            name="Start",
            value="",
            description="The node marking where the chain starts",
            group="Scene",
        )

        self.declare_input(
            name="End",
            value="",
            description="The node marking where the chain ends",
            group="Scene",
        )

        self.declare_option(
            name="Description",
            value="chain",
            description="Used when naming the joints",
            group="Naming",
            pre_expose=True,
        )

        # -- self.config is the rig's configuration component. Its location
        # -- tokens (middle, left, right...) are what LocationSelector offers.
        self.declare_option(
            name="Location",
            value=self.config.middle,
            description="The location (side) token used when naming the joints",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Joint Count",
            value=4,
            description="How many joints to create, including the start and end joints",
            group="Behaviour",
            pre_expose=True,
        )

        # -- Key idea: an OUTPUT is a value this component promises to fill in
        # -- while it runs. Other components can wire their inputs to it, so
        # -- they always get the joints this component actually made, even if
        # -- the names change. is_default marks the output used when another
        # -- component is hooked up to this one without naming an output.
        self.declare_output(
            name="Root Joint",
            description="The first joint in the chain",
            is_default=True,
        )
        self.declare_output(
            name="Tip Joint",
            description="The last joint in the chain",
        )
        self.declare_output(
            name="Joints",
            description="Every joint in the chain, from root to tip",
        )

    def option_widget(self, option_name):
        """
        Returns a location selector for Location and a limited spin box for
        Joint Count.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(
                self.config,
                value=self.option("Location").get(),
            )

        if option_name == "Joint Count":
            return aniseed.widgets.LimitedInteger(minimum=2, maximum=50)

        return None

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the Parent, Start and End inputs.
        """
        if requirement_name in ("Parent", "Start", "End"):
            return aniseed.widgets.ObjectSelector(component=self)
        return None

    def is_valid(self) -> bool:
        """
        Checks the Start, End and Parent nodes exist (when they are not wired
        to another component) and that there are at least two joints.
        """
        for input_name in ("Parent", "Start", "End"):
            node_input = self.input(input_name)

            # -- Wired inputs can only be checked once the build is running
            if node_input.is_address() or not node_input.get():
                continue

            if not cmds.objExists(node_input.get()):
                log.warning(f"{self.label()} : {input_name} {node_input.get()!r} does not exist")
                return False

        if self.option("Joint Count").get() < 2:
            log.warning(f"{self.label()} : Joint Count must be at least 2")
            return False

        return True

    def run(self):
        """
        Creates the joints, orients them down the chain, parents the chain and
        fills in the outputs.
        """
        start = cmds.xform(self.input("Start").get(), query=True, worldSpace=True, translation=True)
        end = cmds.xform(self.input("End").get(), query=True, worldSpace=True, translation=True)
        count = self.option("Joint Count").get()

        # -- cmds.joint parents each new joint to the selected joint, which is
        # -- how it builds a chain. Clear the selection first, so the chain
        # -- does not end up under whatever the user had selected.
        cmds.select(clear=True)

        joints = []
        for index in range(count):

            # -- How far along the chain this joint is, from 0.0 to 1.0
            blend = index / (count - 1)
            position = [s + (e - s) * blend for s, e in zip(start, end)]

            # -- Never hard code names. The configuration decides how names
            # -- look (md_jnt_chain_01 with the Dev Example configuration,
            # -- JNT_Chain_01_MD with the Standard one) and, by default,
            # -- increments the counter until the name is unique in the scene.
            name = self.config.generate_name(
                classification=self.config.joint,
                description=self.option("Description").get(),
                location=self.option("Location").get(),
            )

            joints.append(cmds.joint(name=name, position=position))

        cmds.select(clear=True)

        # -- Aim each joint's X axis at its child, with Y towards world up.
        # -- The tip joint has no child to aim at, so give it the same
        # -- orientation as its parent.
        cmds.joint(
            joints[0],
            edit=True,
            orientJoint="xyz",
            secondaryAxisOrient="yup",
            children=True,
            zeroScaleOrient=True,
        )
        cmds.setAttr(f"{joints[-1]}.jointOrient", 0, 0, 0)

        parent = self.input("Parent").get()
        if parent:
            # -- cmds.parent returns the new name of the node it moved
            joints[0] = cmds.parent(joints[0], parent)[0]

        # -- Fill in the outputs. These must be plain values (strings,
        # -- numbers, lists) as other components read them, and the app shows
        # -- them.
        self.output("Root Joint").set(joints[0])
        self.output("Tip Joint").set(joints[-1])
        self.output("Joints").set(joints)

        log.info(f"{self.label()} created {len(joints)} joints")
        return True
