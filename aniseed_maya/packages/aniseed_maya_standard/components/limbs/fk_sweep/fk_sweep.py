"""
Provides the "Limb : Fk Sweep" component, which walks a joint hierarchy and
creates a standard fk control (optionally with an offset control) for every
joint which is not already constrained. Controls are parented under the
driver of the parent joint and named from regex matches on the joint names.
"""
import re
import logging
import mref
import aniseed
import aniseed_toolkit

log = logging.getLogger(__name__)


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
        """
        Declares the hierarchy root input, the regex options used to extract
        the description, counter and location from joint names (plus an
        ignore regex), the control shape and the offset control option.
        """
        super().__init__(*args, **kwargs)

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
            name="Ignore Regex",
            value="",
        )

        self.declare_option(
            name="Shape",
            value="core_cube",
            group="Visuals",
        )

        self.declare_option(
            name="Add Offset Control",
            description=(
                "If enabled, a second control is created and parented under "
                "the main control. The offset control becomes the driving "
                "control for the joint, letting animators add layered offsets "
                "on top of the main control."
            ),
            value=False,
            group="Behaviour",
            pre_expose=True,
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the hierarchy root input.
        """
        if requirement_name == "Hierarchy Root":
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        """
        This allows us to return different widgets for different options.
        """
        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(self.option("Shape").get())

    def is_valid(self) -> bool:
        """
        Checks that the hierarchy root exists, that the regexes compile and
        that the name of every joint which will get a control matches the
        description, location and counter regexes.
        """
        hierarchy_root = self.input("Hierarchy Root").get()

        if not hierarchy_root or not mref.objExists(hierarchy_root):
            log.warning(f"{self.label()} : Hierarchy Root is not set or does not exist")
            return False

        try:
            regexes = self._compile_regexes()
        except re.error as error:
            log.warning(f"{self.label()} : one of the regex options is not valid ({error})")
            return False

        for joint in self._joints_to_drive(mref.get(hierarchy_root), regexes["ignore"]):
            if not self._extract_naming(joint.name(), regexes):
                log.warning(
                    f"{self.label()} : could not extract the description, location "
                    f"and counter from '{joint.name()}' using the extraction regexes"
                )
                return False

        return True

    def run(self):
        """
        Walks the joints below (and including) the hierarchy root, parents
        first, and creates a control for each joint which is not already
        constrained and not matched by the ignore regex. Each control is
        parented under the driver of the parent joint's first constraint and
        named using the regex extracted description, location and counter.
        Joints whose parent is not constrained will cause an error.
        """

        hierarchy_root = mref.get(self.input("Hierarchy Root").get())
        shape = self.option("Shape").get()

        regexes = self._compile_regexes()

        for joint in self._joints_to_drive(hierarchy_root, regexes["ignore"]):

            joint_name = joint.name()

            # -- To reach here we have a joint which is not driven, so lets
            # -- get the driver of the parent joint
            driver = joint.parent().constraints()[0].drivers()[0]

            # -- Pull out the naming classifications
            description, location, counter = self._extract_naming(joint_name, regexes)

            # -- Lets build a control for this joint
            control = aniseed_toolkit.rig.control.create(
                description=description,
                location=location,
                counter=counter,
                parent=driver.full_name(),
                match_to=joint.full_name(),
                shape=shape,
                config=self.config,
            )
            driver = control.ctl

            if self.option("Add Offset Control").get():
                driver = aniseed_toolkit.rig.control.add_offset_control(
                    control,
                    description=description,
                    location=location,
                    config=self.config,
                    shape=shape,
                    match_to=joint_name,
                ).ctl

            # -- Now constrain the joint to the control
            aniseed_toolkit.scene.constraints.parent_and_scale(
                driver,
                joint,
                maintain_offset=True,
            )

    def _compile_regexes(self) -> dict:
        """
        Compiles the regex options. The ignore regex is None when the option
        is empty. Raises re.error if any of them is not a valid regex.
        """
        ignore_regex = None
        if self.option("Ignore Regex").get():
            ignore_regex = re.compile(self.option("Ignore Regex").get())

        return dict(
            description=re.compile(self.option("Description Extraction Regex").get()),
            location=re.compile(self.option("Location Extraction Regex").get()),
            counter=re.compile(self.option("Counter Extraction Regex").get()),
            ignore=ignore_regex,
        )

    @staticmethod
    def _joints_to_drive(hierarchy_root, ignore_regex) -> list:
        """
        Returns the hierarchy root and the joints below it, sorted by depth so
        parents always come before their children, leaving out any joints
        which are already constrained or whose name matches the ignore regex.
        """
        joints = hierarchy_root.children(recursive=True, node_type="joint")
        joints = sorted(joints, key=lambda x: x.full_name().count("|"))
        joints.insert(0, hierarchy_root)

        return [
            joint
            for joint in joints
            if not joint.constraints()
            and not (ignore_regex and ignore_regex.search(joint.name()))
        ]

    @staticmethod
    def _extract_naming(joint_name: str, regexes: dict):
        """
        Returns the description, location and counter extracted from the
        joint name by the regexes, or None if any of them does not match (or
        the counter is not a number).
        """
        description_match = regexes["description"].search(joint_name)
        location_match = regexes["location"].search(joint_name)
        counter_match = regexes["counter"].search(joint_name)

        if not description_match or not location_match or not counter_match:
            return None

        try:
            return (
                description_match.groups()[0],
                location_match.groups()[0],
                int(counter_match.groups()[0]),
            )
        except (IndexError, ValueError):
            return None
