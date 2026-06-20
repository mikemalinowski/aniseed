import mref
import aniseed
from maya import cmds


class ExposeJointDrawStyle(aniseed.RigComponent):
    """
    Adds a channel-box (non-keyable) integer attribute to a host node and
    connects it to the ``drawStyle`` attribute on every joint found under
    (and including) a given joint root. This lets animators toggle joint
    visibility for a whole hierarchy from a single control.
    """

    identifier = "Utility : Expose Joint Draw Style"

    def __init__(self, *args, **kwargs):
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
        if requirement_name in ("Attribute Host", "Joint Root"):
            return aniseed.widgets.ObjectSelector()

        return None

    def run(self):
        host_name = self.input("Attribute Host").get()
        joint_root = self.input("Joint Root").get()
        attribute_name = self.option("Attribute Name").get()
        default_value = self.option("Default Value").get()

        attribute = mref.get(host_name).add_attribute(
            attribute_name,
            value=default_value,
            attribute_type="long",
            keyable=False,
        )
        attribute.set(channelBox=True)

        joints = [joint_root]
        joints.extend(
            cmds.listRelatives(joint_root, allDescendents=True, type="joint") or []
        )

        for joint in joints:
            attribute.connect(
                mref.get(joint).attr("drawStyle"),
                force=True,
            )