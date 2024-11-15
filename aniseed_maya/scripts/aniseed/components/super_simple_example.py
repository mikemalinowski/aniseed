import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
class SuperSimpleExampleComponent(aniseed.RigComponent):

    identifier = "Super Simple Example"

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(SuperSimpleExampleComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description="The parent for the control hierarchy",
            validate=True,
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Bone",
            description="The root of the spine",
            validate=True,
            value="",
            group="Required JointsX",
        )

        self.declare_output(name="Control")

    def input_widget(self, requirement_name: str):
        if requirement_name in ["Parent", "Bone"] :
            return aniseed.widgets.everywhere.ObjectSelector(component=self)

    # ----------------------------------------------------------------------------------
    def run(self):

        parent = self.input("Parent").get()
        bone = self.input("Bone").get()

        # -- Create a node
        my_control_node = mc.rename(
            mc.spaceLocator(),
            "MyAwesomeControl",
        )

        mc.parentConstraint(
            my_control_node,
            bone,
            maintainOffset=True,
        )

        self.output("Control").set(my_control_node)

        return True