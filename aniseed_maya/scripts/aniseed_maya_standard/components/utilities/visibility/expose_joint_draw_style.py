"""
Provides the "Utility : Expose Joint Draw Style" component, which adds a
channel box integer attribute to a host node and connects it to the
drawStyle of every joint in a hierarchy, so the joints can be shown or
hidden from a single control.
"""
import mref
import aniseed


class ExposeJointDrawStyle(aniseed.RigComponent):
    """
    Adds a channel-box (non-keyable) integer attribute to a host node and
    connects it to the ``drawStyle`` attribute on every joint found under
    (and including) a given joint root. This lets animators toggle joint
    visibility for a whole hierarchy from a single control.
    """

    identifier = "Utility : Expose Joint Draw Style"

    def __init__(self, *args, **kwargs):
        """
        Declares the Attribute Host and Joint Root inputs and the Attribute Name
        and Default Value options.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Attribute Host",
            value="",
            description="The node the new attribute will be added to (typically a control).",
        )

        self.declare_input(
            name="Joint Root",
            value="",
            description=(
                "The top joint of the hierarchy. The new attribute will drive "
                "``drawStyle`` on this joint and every joint under it."
            ),
        )

        self.declare_option(
            name="Attribute Name",
            value="jointDrawStyle",
            description="The long name of the attribute to add to the host.",
        )

        self.declare_option(
            name="Default Value",
            value=0,
            description=(
                "Initial value applied to the new attribute (and therefore "
                "to drawStyle on the joint hierarchy). Maya drawStyle: "
                "0 = Bone, 1 = Multi-child as Box, 2 = None."
            ),
        )

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the Attribute Host and Joint Root inputs,
        and None for anything else.
        """
        if requirement_name in ("Attribute Host", "Joint Root"):
            return aniseed.widgets.ObjectSelector()

        return None

    def run(self):
        """
        Adds the integer attribute to the host (shown in the channel box but not
        keyable) and force connects it to the drawStyle of the joint root and
        every joint beneath it.
        """
        joint_root = mref.get(self.input("Joint Root").get())

        attribute = mref.get(self.input("Attribute Host").get()).add_attribute(
            self.option("Attribute Name").get(),
            value=self.option("Default Value").get(),
            attribute_type="long",
            keyable=False,
        )
        attribute.set(channelBox=True)

        joints = [joint_root]
        joints.extend(joint_root.children(recursive=True, node_type="joint"))

        for joint in joints:
            attribute.connect(
                joint.attr("drawStyle"),
                force=True,
            )