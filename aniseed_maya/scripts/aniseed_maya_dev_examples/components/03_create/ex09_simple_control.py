"""
Provides the "Dev Example : Simple Control" component, which creates a single
control and uses it to drive a joint, using only maya.cmds.

This is the "real rig component" example. It does the same job as the
standard "Basic : Singular" component, without aniseed_toolkit.

What this example teaches:
    * Building an org > zero > control hierarchy, named by the configuration
    * Wiring components together: addresses, and hook_to_parent
    * Default outputs
    * Suggesting a label with suggested_label

Read next: ex10_utility_network.py
"""
import logging

# -- maya.cmds is the only Maya API this example uses
from maya import cmds

import aniseed

log = logging.getLogger(__name__)


class SimpleControl(aniseed.RigComponent):
    """
    Creates a circle control, with an org and zero group above it, at the
    joint's position, and parent and scale constrains the joint to it.
    """

    identifier = "Dev Example : Simple Control"

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent and Joint to Drive inputs, the naming, shape and
        behaviour options, and the Org, Zero and Control outputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the control's org group is parented under",
            group="Scene",
        )

        self.declare_input(
            name="Joint to Drive",
            value="",
            description="The joint the control is placed at, and drives",
            group="Scene",
        )

        self.declare_option(
            name="Description",
            value="demo",
            description="Used when naming the control and its groups",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            value=self.config.middle,
            description="The location (side) token used when naming",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Radius",
            value=2.0,
            description="The radius of the control's circle",
            group="Visuals",
        )

        self.declare_option(
            name="Align To World",
            value=False,
            description="If on, the control is placed at the joint but keeps world orientation",
            group="Behaviour",
        )

        self.declare_option(
            name="Drive Joint",
            value=True,
            description="If on, the joint is parent and scale constrained to the control",
            group="Behaviour",
        )

        self.declare_output(
            name="Org",
            description="The top group, which places the control in the rig",
        )
        self.declare_output(
            name="Zero",
            description="The group directly above the control, so the control can be zeroed",
        )

        # -- This is the default output, so when another component is hooked
        # -- up to this one (such as a component added beneath it in the
        # -- stack), it gets the control rather than one of the groups
        self.declare_output(
            name="Control",
            description="The control the animator uses",
            is_default=True,
        )

    def option_widget(self, option_name):
        """
        Returns a location selector for the Location option.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(
                self.config,
                value=self.option("Location").get(),
            )
        return None

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the Parent and Joint to Drive inputs.
        """
        if requirement_name in ("Parent", "Joint to Drive"):
            return aniseed.widgets.ObjectSelector(component=self)
        return None

    def on_enter_stack(self):
        """
        When the user adds this component beneath another one (such as a
        joint chain), wires Joint to Drive to that component's root joint.
        """
        super().on_enter_stack()

        # -- Key idea: an input can hold an ADDRESS instead of a value. An
        # -- address looks like "[Joint Chain].[output].[Root Joint]" (the
        # -- component label, the kind of attribute, and its name) and .get()
        # -- returns whatever that attribute holds at the time. This is how
        # -- components are wired together. Note that the address uses the
        # -- label, so renaming a component breaks the addresses pointing at
        # -- it, and labels must not contain a full stop (the address is split
        # -- on them).
        # --
        # -- hook_to_parent writes that address for us. It looks for an output
        # -- on the parent component whose name contains one of the tags, and
        # -- falls back to the parent's default output.
        joint_input = self.input("Joint to Drive")

        # -- Only do this if the user has not already chosen a joint
        if not joint_input.get(resolved=False):
            joint_input.hook_to_parent(tags=["root", "joint"])

    def suggested_label(self):
        """
        Suggests a label from the description and location, such as
        "Demo Control MD".
        """
        description = self.option("Description").get().replace("_", " ").title()
        return f"{description} Control {self.option('Location').get().upper()}"

    def is_valid(self) -> bool:
        """
        Checks the Parent and Joint to Drive nodes exist, when they are not
        wired to another component.
        """
        for input_name in ("Parent", "Joint to Drive"):
            node_input = self.input(input_name)

            # -- Wired inputs can only be checked once the build is running,
            # -- and empty ones are reported by the required input check
            if node_input.is_address() or not node_input.get():
                continue

            if not cmds.objExists(node_input.get()):
                log.warning(f"{self.label()} : {input_name} {node_input.get()!r} does not exist")
                return False

        return True

    def run(self):
        """
        Creates the org, zero and control, places them at the joint and
        constrains the joint to the control.
        """
        description = self.option("Description").get()
        location = self.option("Location").get()
        joint = self.input("Joint to Drive").get()

        # -- The configuration's classification tokens (organisational,
        # -- zero, control...) mean the names follow whatever convention the
        # -- rig uses
        org = cmds.createNode(
            "transform",
            name=self.config.generate_name(self.config.organisational, description, location),
            parent=self.input("Parent").get(),
        )

        zero = cmds.createNode(
            "transform",
            name=self.config.generate_name(self.config.zero, description, location),
            parent=org,
        )

        # -- constructionHistory=False leaves a plain curve, without the
        # -- makeNurbsCircle node which would otherwise keep driving its shape.
        # -- The normal points down X, as that is the axis the joint aims along.
        control = cmds.circle(
            name=self.config.generate_name(self.config.control, description, location),
            normal=(1, 0, 0),
            radius=self.option("Radius").get(),
            constructionHistory=False,
        )[0]

        # -- relative=True keeps the control's zero values, so it sits
        # -- exactly on the zero group
        control = cmds.parent(control, zero, relative=True)[0]

        # -- Moving the org (rather than the control) means the control's own
        # -- values stay at zero, which is what animators expect
        cmds.matchTransform(
            org,
            joint,
            position=True,
            rotation=not self.option("Align To World").get(),
        )

        if self.option("Drive Joint").get():
            cmds.parentConstraint(control, joint, maintainOffset=True)
            cmds.scaleConstraint(control, joint, maintainOffset=True)

        self.output("Org").set(org)
        self.output("Zero").set(zero)
        self.output("Control").set(control)

        return True
