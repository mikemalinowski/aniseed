"""
Provides the "Augment : Dynamic Pivot" component, which builds a control
whose pivot slides along a guide curve to the point its rotation tips towards
(see aniseed_cartoon.rigging.dynamic_pivot), and the "Augment : Dynamic Foot
Pivot" component, which extends it with a heel roll and toe to drive a foot.
"""
import mref
import logging
import aniseed
import aniseed_utilities as au
from aniseed_cartoon.rigging import dynamic_pivot

log = logging.getLogger(__name__)


class DynamicPivotComponent(aniseed.RigComponent):
    """
    Builds a pivot control which rocks around the Guide Curve. Rotating the
    control in x and z moves its pivot to the point on the curve the rotation
    tips towards. The guide curve is duplicated, and is assumed to lie flat
    in the xz plane with z forward.

    The Result output follows the rocking, and is the node to drive things
    (such as a foot) from. If a Driven Joint is given it is constrained to
    the Result, and one can be created on stack entry with Create Joint.
    """

    identifier = "Augment : Dynamic Pivot"

    def __init__(self, *args, **kwargs):
        """
        Declares the parent, guide curve and driven joint inputs, the naming,
        debug and joint creation options and the "Pivot" and "Result" outputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the pivot setup",
            validate=True,
            group="Control Rig",
        )

        self.declare_input(
            name="Guide Curve",
            description="The curve the pivot slides along, lying in the xz plane with z forward",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="Driven Joint",
            description="Optional joint which is constrained to the Result",
            validate=False,
            group="Optional Joints",
        )

        self.declare_option(
            name="Descriptive Prefix",
            description="Prefix used when naming the controls and mechanical nodes",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            description="Location token (e.g. md/lf/rt) applied to generated node names",
            value=self.config.middle,
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Debug",
            description="If True, a sphere is created which sits at the pivot point",
            value=False,
            group="Behaviour",
        )

        self.declare_option(
            name="Create Joint",
            description="If true, a joint is created under the selection on stack entry and set as the Driven Joint",
            value=True,
            group="Creation",
            pre_expose=True,
        )

        self.declare_output(
            name="Pivot",
            description="The pivot control",
        )

        self.declare_output(
            name="Result",
            description="The node which follows the rocking of the pivot control",
            is_default=True,
        )

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output and
        hides the Create Joint option. If it is enabled, a joint is created
        under (and matched to) the selection, or at the world if nothing is
        selected, and set as the Driven Joint.
        """
        self.option("Create Joint").set_hidden(True)
        self.input("Parent").hook_to_parent()

        if self.option("Create Joint").get():
            selected = au.core.selection.first_selected()
            self.input("Driven Joint").set(
                au.scene.joints.create(
                    description=f"{self.option('Descriptive Prefix').get()}DynamicPivot",
                    location=self.option("Location").get(),
                    parent=selected,
                    config=self.config,
                    match_to=selected,
                ),
            )

    def option_widget(self, option_name: str):
        """
        This allows us to provide dedicate widgets for specific options
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config, self.option(option_name).get())

    def input_widget(self, requirement_name):
        """
        Every input is a single node
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def is_valid(self) -> bool:
        """
        Checks the guide curve is set and is a nurbs curve, and that the
        driven joint exists if it is given.
        """
        driven_joint = self.input("Driven Joint").get()

        if driven_joint and not mref.objExists(driven_joint):
            log.warning(f"{self.label()}: The Driven Joint ({driven_joint}) does not exist")
            return False

        return self._guide_is_valid()

    def _guide_is_valid(self) -> bool:
        """
        Checks the guide curve is set and is a nurbs curve
        """
        guide = self.input("Guide Curve").get()

        if not guide or not mref.objExists(guide):
            log.warning(f"{self.label()}: The Guide Curve must be set to an existing curve")
            return False

        if not mref.listRelatives(guide, shapes=True, type="nurbsCurve", noIntermediate=True):
            log.warning(f"{self.label()}: The Guide Curve ({guide}) is not a nurbs curve")
            return False

        return True

    def run(self) -> bool:
        """
        Builds the dynamic pivot, constrains the driven joint (if given) to
        its result and sets the outputs to its control and result.
        """
        setup = dynamic_pivot.DynamicPivot(
            guide_curve=self.input("Guide Curve").get(),
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            debug=self.option("Debug").get(),
            parent=self.input("Parent").get(),
        ).build()

        driven_joint = self.input("Driven Joint").get()
        if driven_joint:
            au.scene.constraints.parent_and_scale(setup.anchor, driven_joint, maintain_offset=True)

        self.output("Pivot").set(setup.control.ctl)
        self.output("Result").set(setup.anchor)
        return True


class DynamicFootPivotComponent(DynamicPivotComponent):
    """
    A Dynamic Pivot which drives a foot and toe joint. Rotating the pivot
    control forward in x first lifts the heel, rolling the foot around the
    toe, until it reaches the control's heelRollLimit, after which the rest
    rocks the pivot as normal. Heel and Toe controls give direct control of
    each (see aniseed_cartoon.rigging.dynamic_pivot.DynamicFootPivot).

    The Result output is the node the foot joint follows.
    """

    identifier = "Augment : Dynamic Foot Pivot"

    def __init__(self, *args, **kwargs):
        """
        Replaces the Driven Joint with the Foot Joint and Toe Joint inputs and
        adds the "Heel" and "Toe" outputs
        """
        super().__init__(*args, **kwargs)

        self.inputs().remove(self.input("Driven Joint"))

        self.declare_input(
            name="Foot Joint",
            description="The foot joint, which is constrained to the Result",
            validate=True,
            group="Required Joints",
        )

        self.declare_input(
            name="Toe Joint",
            description="The toe joint, which the heel rolls around and the Toe control drives",
            validate=True,
            group="Required Joints",
        )

        self.declare_output(
            name="Heel",
            description="The heel control",
        )

        self.declare_output(
            name="Toe",
            description="The toe control",
        )

    def on_enter_stack(self):
        """
        Hooks the Parent input to the parent component's default output and
        hides the Create Joint option. If it is enabled, a foot joint is
        created under (and matched to) the selection, with a toe joint under
        it, and they are set as the Foot Joint and Toe Joint.
        """
        self.option("Create Joint").set_hidden(True)
        self.input("Parent").hook_to_parent()

        if not self.option("Create Joint").get():
            return

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()
        selected = au.core.selection.first_selected()

        foot = au.scene.joints.create(
            description=f"{prefix}Foot",
            location=location,
            parent=selected,
            config=self.config,
            match_to=selected,
        )

        toe = au.scene.joints.create(
            description=f"{prefix}Toe",
            location=location,
            parent=foot,
            config=self.config,
            match_to=foot,
        )

        self.input("Foot Joint").set(foot)
        self.input("Toe Joint").set(toe)

    def is_valid(self) -> bool:
        """
        Checks the foot and toe joints exist and the guide curve is valid
        """
        for name in ["Foot Joint", "Toe Joint"]:
            joint = self.input(name).get()

            if not joint or not mref.objExists(joint):
                log.warning(f"{self.label()}: The {name} must be set to an existing joint")
                return False

        return self._guide_is_valid()

    def run(self) -> bool:
        """
        Builds the dynamic foot pivot, constrains the foot joint to its
        result and the toe joint to its toe control, and sets the outputs
        """
        foot_joint = self.input("Foot Joint").get()
        toe_joint = self.input("Toe Joint").get()

        setup = dynamic_pivot.DynamicFootPivot(
            guide_curve=self.input("Guide Curve").get(),
            config=self.config,
            prefix=self.option("Descriptive Prefix").get(),
            location=self.option("Location").get(),
            foot=foot_joint,
            toe=toe_joint,
            debug=self.option("Debug").get(),
            parent=self.input("Parent").get(),
        ).build()

        au.scene.constraints.parent_and_scale(setup.foot_anchor, foot_joint, maintain_offset=True)
        au.scene.constraints.parent_and_scale(setup.toe_control.ctl, toe_joint, maintain_offset=True)

        self.output("Pivot").set(setup.control.ctl)
        self.output("Heel").set(setup.heel_control.ctl)
        self.output("Toe").set(setup.toe_control.ctl)
        self.output("Result").set(setup.foot_anchor)
        return True
