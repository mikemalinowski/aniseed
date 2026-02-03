import re
import typing
import crosswalk

from . import component
from . import widgets


def ignore(name: typing.Any) -> str:
    """
    callable that does nothing
    """
    return name


def camel_to_snake(name: str) -> str:
    """
    Will convert a camel case string to a snake case string
    """
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def title(name: str) -> str:
    """
    Will convert a snake case string to a camel case string
    """
    if name[0].isupper() and "_" not in name:
        return name

    return name.title()


class RigConfiguration(component.RigComponent):
    """
    The RigConfiguration is a special Rig Component. Every Rig instance must have a rig
    configuration item in its stack in order to build.

    This configuration will expose all its parameters to the user to tailor. Alternatively
    you can implement your own components providing you exose all the same properties and
    methods.

    If you implement your own config compnent it should always start wtih "Rig Configuration :"
    """
    identifier = "Rig Configuration : Standard"
    version = 1

    def __init__(self, *args, **kwargs):
        super(RigConfiguration, self).__init__(*args, **kwargs)

        self.naming_items = {
            "organisational_label": "org",
            "control_label": "ctl",
            "joint_label": "jnt",
            "zero_label": "zro",
            "offset_label": "off"
        }

        for label, value in self.naming_items.items():
            self.declare_option(
                name=label,
                value=value,
                group="Classification Labels"
            )

        self.location_items = {
            "left_location": "lf",
            "right_location": "rt",
            "middle_location": "md",
            "front_location": "fr",
            "back_location": "bk",
        }

        for label, value in self.location_items.items():
            self.declare_option(
                name=label,
                value=value,
                group="Location Labels"
            )

        self.declare_option(
            name="rule",
            value="{classification}_{description}_{counter}_{location}",
            group="Naming Format"
        )

        self.styling = {
            "classification_style": "upper",
            "description_style": "titled",
            "counter_style": "ignore",
            "location_style": "upper",
        }

        for label, value in self.styling.items():
            self.declare_option(
                name=label,
                value=value,
                group="Segment Styling"
            )

        self.declare_option(
            name="counter_padding",
            value=2,
            group="Naming Format"
        )

        self.declare_option(
            name="decomposition_map",
            value=dict(),
            hidden=True,
        )
        self._decomposition_map = dict()

    # ----------------------------------------------------------------------------------
    # This MUST be re-implemented
    def run(self) -> bool:
        """
        This should be re-implemented in your component and should contain all the
        code which you want to trigger during the build.
        """
        # -- Reset the decomposition map on build
        self.option("decomposition_map").set(dict())
        return True

    def is_valid(self) -> bool:

        # -- We only allow one config per rig
        config_count = 0

        for component_ in self.rig.components():
            if component_.identifier.startswith("Rig Configuration : "):
                config_count += 1

        if config_count > 1:
            print(f"There are {config_count} configs. You are only allowed one.")
            return False

        return True

    def option_widget(self, option_name: str):

        if option_name in self.styling:
            return widgets.ItemSelector(
                [
                    "lower",
                    "upper",
                    "titled",
                    "ignore",
                ],
                default_item=self.styling[option_name],
            )

    @property
    def organisational(self):
        return self.option("organisational_label").get()

    @property
    def control(self):
        return self.option("control_label").get()

    @property
    def joint(self):
        return self.option("joint_label").get()

    @property
    def zero(self):
        return self.option("zero_label").get()

    @property
    def offset(self):
        return self.option("offset_label").get()

    @property
    def left(self):
        return self.option("left_location").get()

    @property
    def right(self):
        return self.option("right_location").get()

    @property
    def middle(self):
        return self.option("middle_location").get()

    @property
    def front(self):
        return self.option("front_location").get()

    @property
    def back(self):
        return self.option("back_location").get()

    @property
    def rule(self):
        return self.option("rule").get()

    def create_component_structure(self):
        global_joint = crosswalk.items.create(
            self.generate_name(
                classification=self.joint,
                description="GlobalSrt",
                location=self.middle,
            ),
        )

        # -- Lets pre-load our Standard rigs with a series of components
        sub_struct = self.rig.add_component(
            component_type="Utility : Add Sub Structure",
            label="Define Rig Structure",
            inputs={
                "Parent": crosswalk.items.get_name(self.rig.host()),
            },
            options={
                "Sub Nodes": [
                    "skeleton",
                    "controls",
                    "geometry",
                    "guides",
                ]
            },
        )

        self.rig.add_component(
            component_type="Utility : Reparent",
            label="Parent Skeleton",
            inputs={
                "Node To Re-Parent": crosswalk.items.get_name(global_joint),
                "New Parent": self.generate_name(
                    classification=self.organisational,
                    description="skeleton",
                    location=self.middle,
                )
            },
            parent=sub_struct,
        )

        make_editable = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Make Rig Editable",
        )

        self.rig.add_component(
            component_type="Utility : Delete Children",
            label="Clear Control Rig",
            inputs={
                "Node": self.generate_name(
                    classification=self.organisational,
                    description="controls",
                    location=self.middle,
                ),
            },
            parent=make_editable,
        )

        build_rig = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Build Control Rig",
        )

    def user_functions(self) -> typing.Dict[str, callable]:
        return {
            "Create Initial Component Structure": self.create_component_structure,
        }

    def apply_style(self, str_value, format_type):

        if format_type == "ignore":
            return str_value

        if format_type == "lower":
            return str_value.lower()

        if format_type == "upper":
            return str_value.upper()

        if format_type == "titled":
            return title(str_value)

        if format_type == "snake":
            return camel_to_snake(str_value)

        return str_value

    def generate_name(
            self,
            classification: str,
            description: str,
            location: str,
            counter: int = 1,
            unique: bool = True,
    ) -> str:
        """
        This function will generate a name based on the rules defined in the config.

        If unique is True then the counter will be incremented until a name is found
        that is unique to the scene.
        """
        while True:

            name = self.rule[:].format(
                classification=self.apply_style(classification, self.option("classification_style").get()),
                description=self.apply_style(description, self.option("description_style").get()),
                location=self.apply_style(location, self.option("location_style").get()),
                counter=str(counter).rjust(self.option("counter_padding").get(), "0"))

            if not unique:
                self.store_name_decomposition(
                    name,
                    classification,
                    description,
                    location,
                    counter,
                )
                return name

            if not crosswalk.items.exists(name):
                self.store_name_decomposition(
                    name,
                    classification,
                    description,
                    location,
                    counter,
                )
                return name

            counter += 1

    def on_build_started(self):
        """
        These functions are specific to the rig configuration and allow the
        config node to operate before and after the build.
        """
        # -- During the build we store a dictionary of names generated and the
        # -- parts used to generate them. That allows tools to decompose
        # -- any name generated through this config.
        self._decomposition_map = dict()

    def on_build_finished(self, successful: bool):
        """
        These functions are specific to the rig configuration and allow the
        config node to operate before and after the build.
        """
        # -- At the end of the build we store the decomposition map into a
        # -- hidden option. This allows any tools which later interact
        # -- with the rig to decompose the name
        self.option("decomposition_map").set(self._decomposition_map)

    def store_name_decomposition(
        self,
        name,
        classification,
        description,
        location,
        counter,
    ):
        """
        We store the name decomposition because it allows us to look up name data
        later on through tools.
        """
        self._decomposition_map[name] = dict(
            classification=classification,
            description=description,
            location=location,
            counter=counter,
        )

    def decompose_name(self, name):
        decomposition_map = self.option("decomposition_map").get()

        if name not in decomposition_map:
            print(decomposition_map)
            return None

        return decomposition_map[name]

    def extract_description(self, name: str) -> str:
        """
        This function should always be able to return the descriptive component
        of a name
        """
        parts = [
            p
            for p in re.split(r"\{|\}", self.rule)
            if p and p != "_"
        ]

        description_index = parts.index("description")

        if description_index == 0:
            return "_".join(name.split("_")[:-3])

        if description_index == 3:
            return "_".join(name.split("_")[3:])

        return "_".join("_".join(name.split("_")[description_index:]).split("_")[
                        :-(3 - description_index)])
