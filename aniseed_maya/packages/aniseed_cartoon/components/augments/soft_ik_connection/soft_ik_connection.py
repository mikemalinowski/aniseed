"""
Provides the "Augment : Soft IK Connection" component, which applies soft ik
(with stretch) to an existing two bone ik chain (see
aniseed_cartoon.rigging.soft_ik_connection).
"""
import aniseed
from aniseed_cartoon.rigging import soft_ik_connection


class SoftIkConnectionComponent(aniseed.RigComponent):
    """
    Applies soft ik to a two bone ik chain, by driving the translateX of its
    second and third joints from the distance between the Root and the
    Target. Use it on an ik chain the rig has already built, not on skinned
    joints.

    The soft ik attributes (UpperAddition, LowerAddition, Stretch,
    SoftDistance) are added to the Attribute Host, or to a network node if
    no host is given.
    """

    identifier = "Augment : Soft IK Connection"

    def __init__(self, *args, **kwargs):
        """
        Declares the root, target, joint and attribute host inputs and the
        "Attribute Host" output.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Root",
            description="A node at the root of the chain, such as the ik root control",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="Target",
            description="The ik target, such as the ik control",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="Second Joint",
            description="The second (middle) joint of the ik chain",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="Third Joint",
            description="The third (end) joint of the ik chain",
            validate=True,
            group="Required Nodes",
        )

        self.declare_input(
            name="Attribute Host",
            description=(
                "The node to add the soft ik attributes to, such as the ik control. "
                "If not given, a network node is created to hold them."
            ),
            validate=False,
            group="Behaviour",
        )

        self.declare_output(
            name="Attribute Host",
            description="The node holding the soft ik attributes",
            is_default=True,
        )

    def input_widget(self, requirement_name):
        """
        Every input is a single node
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def run(self) -> bool:
        """
        Builds the soft ik connection and sets the output to its attribute host.
        """
        connection = soft_ik_connection.SoftIkConnection(
            root=self.input("Root").get(),
            target=self.input("Target").get(),
            second_joint=self.input("Second Joint").get(),
            third_joint=self.input("Third Joint").get(),
            host=self.input("Attribute Host").get() or None,
        ).build()

        self.output("Attribute Host").set(connection.host.full_name())
        return True
