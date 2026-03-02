import re
import mref
import aniseed
import aniseed_toolkit
from maya import cmds


class FkSweep(aniseed.RigComponent):
    """
    This will cycle over all the joints in the given hierarchy
    and for any that are not constrained it will generate a control
    and make that control a child of the parent joint's driver.

    This is typically a good way to assign standard FK controls to lots of
    joints quickly that do not need any special behaviour.

    The name of the control will always be derived from the name of
    the joint its driving.
    """

    identifier = 'Limb : Fk Sweep'

    def __init__(self, *args, **kwargs):
        super(FkSweep, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Hierarchy Root",
            value="",
        )

        self.declare_option(
            name="Description Extraction Regex",
            value="_(.*)_[0-9]",
        )

        self.declare_option(
            name="Counter Extraction Regex",
            value="_([0-9]*)_",
        )

        self.declare_option(
            name="Location Extraction Regex",
            value="[0-9]_(.*)$",
        )

        self.declare_option(
            name="Shape",
            value="core_cube",
            group="Visuals",
        )

    def input_widget(self, requirement_name: str):
        if requirement_name == "Hierarchy Root":
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        """
        This allows us to return different widgets for different options.
        """
        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(self.option("Shape").get())

    def run(self):

        hierarchy_root = mref.get(self.input("Hierarchy Root").get())

        # -- Compile our regex
        description_regex = re.compile(self.option("Description Extraction Regex").get())
        location_regex = re.compile(self.option("Location Extraction Regex").get())
        counter_regex = re.compile(self.option("Counter Extraction Regex").get())

        joints = hierarchy_root.children(recursive=True, node_type="joint")
        joints = sorted(joints, key=lambda x: x.full_name().count("|"))


        # -- sort the joints by depth
        for joint in joints:

            is_driven = joint.constraints()
            if is_driven:
                continue

            # -- To reach here we have a joint which is not driven, so lets
            # -- get the parent joint and driver
            parent = joint.parent()
            driver = parent.constraints()[0].drivers()[0]
            joint_name = joint.name()
            #
            # -- Pull out the naming classifications
            description = description_regex.search(joint_name).groups()[0]
            location = location_regex.search(joint_name).groups()[0]
            counter = int(counter_regex.search(joint_name).groups()[0])

            # -- Lets build a control for this joint
            control = aniseed_toolkit.control.create(
                description=description,
                location=location,
                counter=counter,
                parent=driver.full_name(),
                match_to=joint.full_name(),
                shape=self.option("Shape").get(),
                config=self.config,
            )

            # -- Now constraint the joint to the control
            cmds.parentConstraint(
                control.ctl,
                joint.full_name(),
                maintainOffset=True,
            )
            cmds.scaleConstraint(
                control.ctl,
                joint.full_name(),
                maintainOffset=True,
            )
