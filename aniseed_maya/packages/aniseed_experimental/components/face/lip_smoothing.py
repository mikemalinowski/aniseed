"""
Provides the "Face : Lip Smoothing" component, which makes the lips work
together as the jaw opens (the jaw behaviour of "Limb : Face"). A pose
cannot do this, as the jaw can shear. Instead each lip control's zero is
blended between a proxy following the jaw and one following the lips, with
smooth_lips_left and smooth_lips_right attributes on the jaw control (proxied
onto the attribute host) dialling it in and out.
"""
import os
import logging

import mref
import aniseed
import aniseed_utilities as au
from aniseed_experimental.rigging.lip_smoothing import SIDES, SMOOTHING, DRIVER_INPUTS, lip_input_name

log = logging.getLogger(__name__)


class FaceLipSmoothing(aniseed.RigComponent):
    """
    Blends the zero of each lip control between its own space and a proxy
    which follows the jaw and lips, by the smooth_lips attributes added to
    the jaw control.
    """

    identifier = "Face : Lip Smoothing"
    icon = os.path.join(os.path.dirname(__file__), "lip_smoothing.png")

    def __init__(self, *args, **kwargs):
        """
        Declares the jaw, upper and lower lip control, space and attribute
        host inputs, and an input per smoothed lip control.
        """
        super().__init__(*args, **kwargs)

        for input_name, description in [
            ("Jaw Control", "The jaw control, which is given the smooth_lips attributes"),
            ("Upper Lip Control", "The control moving the upper lip as a whole"),
            ("Lower Lip Control", "The control moving the lower lip as a whole"),
            ("Space", "The space the lower lips and dimples blend from (typically the face org)"),
            ("Attribute Host", "The node the smooth_lips attributes are proxied onto"),
        ]:
            self.declare_input(
                name=input_name,
                description=description,
                validate=True,
                group="Control Rig",
            )

        for label, *_ in SMOOTHING:
            for side in SIDES:
                self.declare_input(
                    name=lip_input_name(label, side),
                    description=f"The {side} {label.replace('_', ' ')} control",
                    validate=True,
                    group="Lip Controls",
                )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for every input.
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        """
        Adds the smooth_lips attributes, then for each lip control creates a
        proxy (under a proxy org in the space) constrained between its space
        and what it follows, and constrains the control's zero between its
        org and the proxy, blended by the side's smooth_lips attribute.
        """
        jaw = mref.get(self.input("Jaw Control").get())
        attribute_host = mref.get(self.input("Attribute Host").get())
        drivers = {key: self.input(input_name).get() for key, input_name in DRIVER_INPUTS.items()}

        attribute_host.add_separator_attribute()
        for side in SIDES:
            smooth_attribute = jaw.add_attribute(
                f"smooth_lips_{side}",
                attribute_type="float",
                keyable=True,
                value=1,
            )
            attribute_host.add_proxy(
                smooth_attribute.name(include_node=False),
                source_attribute=smooth_attribute,
            )

        space = mref.get(drivers["space"])
        proxy_org = mref.create(
            "transform",
            name=self.config.generate_name(
                classification=self.config.organisational,
                description="mouth_smoothing_proxy",
                location=self.config.middle,
            ),
            parent=space,
        )
        proxy_org.match_to(space)

        for label, follow, parent_space, weights in SMOOTHING:
            for side in SIDES:
                control_name = self.input(lip_input_name(label, side)).get()
                control = au.rig.control.get(control_name)

                proxy = mref.create(
                    "transform",
                    name=self.config.generate_name(
                        classification=self.config.mechanical,
                        description=mref.get(control.ctl).name() + "_smooth_proxy",
                        location=self.config.middle,
                    ),
                    parent=proxy_org,
                )
                proxy.match_to(mref.get(control.off))

                mref.parentConstraint(drivers[parent_space], proxy, maintainOffset=True)
                constraint = mref.parentConstraint(drivers[follow], proxy, maintainOffset=True)[0]
                constraint.interpType.set(2)  # -- Shortest

                for idx, weight in enumerate(weights):
                    constraint.weight_attributes()[idx].set(weight)

                mref.parentConstraint(control.org, control.zero, maintainOffset=True)
                constraint = mref.parentConstraint(proxy, control.zero, maintainOffset=True)[0]
                constraint.interpType.set(2)  # -- Shortest

                au.scene.constraints.blend_weights(
                    jaw.attr(f"smooth_lips_{side}"),
                    constraint,
                )

        return True
