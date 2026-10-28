"""
Provides the "Utility : Expose Controls As XRay" component, which adds a
boolean toggle attribute to a host node and connects it to the
alwaysDrawOnTop attribute of every control shape in the scene, allowing
X-Ray display of all controls to be toggled from the channel box.
"""
import mref
import aniseed


class XRayNodesExposure(aniseed.RigComponent):
    """
    Adds a boolean toggle attribute to a chosen host node and connects
    it to the alwaysShowOnTop ("X-Ray") attribute of every shape under
    every controller-marked transform in the scene. Flipping the toggle
    on the host node enables or disables X-Ray rendering for every
    control simultaneously.

    The toggle is added as channelBox=True / keyable=False so animators
    can flick it from the channel box without polluting the keyframe
    timeline.
    """

    identifier = "Utility : Expose Controls As XRay"

    def __init__(self, *args, **kwargs):
        """
        Declares the Attribute Host and Attribute Name inputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Attribute Host",
            value="",
            description="The node that the XRay toggle attribute will be added to. Usually a top-level visibility or settings node.",
        )

        self.declare_input(
            name="Attribute Name",
            value="xray_controls",
            description="The name given to the toggle attribute created on the host node.",
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the Attribute Host input.
        """
        if requirement_name == "Attribute Host":
            return aniseed.widgets.ObjectSelector()

    def run(self) -> bool:
        """
        Adds the toggle attribute to the host (or reuses it if it already
        exists) and force connects it to the alwaysDrawOnTop attribute of every
        shape of every controller-linked transform in the scene.
        """
        host = mref.get(self.input("Attribute Host").get())
        attribute_name = self.input("Attribute Name").get()

        # -- Add the toggle attribute on the host (channelBox on, keyable off)
        # -- or reuse it if it already exists from a previous build.
        host_attribute = host.attr(attribute_name)
        if host_attribute is None:
            host_attribute = host.add_attribute(
                attribute_name,
                value=False,
                attribute_type="bool",
                keyable=False,
            )
            host_attribute.set(channelBox=True)

        # -- For every "controller" dependency node in the scene, follow its
        # -- controllerObject plug back to the linked transform and connect the
        # -- host toggle into every shape's alwaysDrawOnTop. force=True so
        # -- re-runs cleanly overwrite any existing connections.
        for controller_node in mref.ls(type="controller"):
            for transform in controller_node.controllerObject.inputs():
                for shape in transform.node().shapes():
                    host_attribute.connect(shape.alwaysDrawOnTop, force=True)

        return True
