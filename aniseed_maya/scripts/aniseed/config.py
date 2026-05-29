import crosswalk

from . import component


class NamingConventionError(ValueError):
    """
    Raised when a name does not match the
    [location]_[classification]_[description]_[counter] format that
    :meth:`RigConfiguration.generate_name` produces.
    """
    pass


class RigConfiguration(component.RigComponent):
    """
    This configuration will create a name in the form of

        [side]_[classification]_[description]_[##]
    """
    identifier =  "Rig Configuration"

    # -- Locations
    left = "l"
    right = "r"
    middle = "c"
    front = "f"
    back = "b"

    # -- Base Types
    organisational = "org"
    control = "ctrl"
    joint = "jnt"
    zero = "zero"
    offset = "off"
    mechanical = "mech"

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
        if hasattr(self, location):
            location = getattr(self, location)

        if hasattr(self, classification):
            classification = getattr(self, classification)

        while True:
            formatted_counter = str(counter).rjust(2, "0")
            name = f"{location.lower()}_{classification}_{description.lower()}_{formatted_counter}"

            if not unique or not crosswalk.items.exists(name):
                return name
            counter += 1

    def extract_location(self, name: str) -> str:
        try:
            return name.split("_")[0]
        except (IndexError, ValueError) as exc:
            raise NamingConventionError(
                f"Could not extract location from {name!r}"
            ) from exc

    def extract_classification(self, name: str) -> str:
        try:
            return name.split("_")[1]
        except (IndexError, ValueError) as exc:
            raise NamingConventionError(
                f"Could not extract classification from {name!r}"
            ) from exc

    def extract_description(self, name: str) -> str:
        try:
            return "_".join(name.split("_")[2:-1])
        except (IndexError, ValueError) as exc:
            raise NamingConventionError(
                f"Could not extract description from {name!r}"
            ) from exc

    def extract_counter(self, name: str) -> int:
        try:
            return int(name.split("_")[-1])
        except (IndexError, ValueError) as exc:
            raise NamingConventionError(
                f"Could not extract counter from {name!r}"
            ) from exc

    def decomposition(self, name):
        return dict(
            location=self.extract_location(name),
            classification=self.extract_classification(name),
            description=self.extract_description(name),
            counter=self.extract_counter(name),
        )

    def on_enter_stack(self):
        if len(self.stack.components()) == 1:
            self.create_default_stack()

    def create_default_stack(self):

        control_org_name = self.generate_name(
            classification=self.organisational,
            description="controls",
            location=self.middle,
        )

        skeleton_org_name = self.generate_name(
            classification=self.organisational,
            description="skeleton",
            location=self.middle,
        )

        # -- Create the edit structure
        edit_component = self.create_editable_structure(None, skeleton_org_name, control_org_name)
        build_component = self.create_rig_structure(None, skeleton_org_name, control_org_name)
        srt_component = self.rig.get_component_by_label("Global SRT")
        reparent_component = self.rig.get_component_by_label("Parent Skeleton")
        created_joint = srt_component.input("Joint To Drive").get()
        reparent_component.input("Node To Re-Parent").set(created_joint)

        self.stack.build()
        self.stack.build(build_below=edit_component)

        # -- Finally select the root joint for the user
        crosswalk.selection.select(created_joint)
        return

    def create_editable_structure(self, parent, skeleton_org_name, control_org_name):

        make_editable = self.rig.add_component(
            component_type="Stack : Execution Block",
            label="Make Rig Editable",
        )

        construction_org = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Rig Hierarchy",
            parent=make_editable,
        )

        # -- Lets pre-load our Standard rigs with a series of components
        self.rig.add_component(
            component_type="Utility : Add Sub Structure",
            label="Define Rig Structure",
            inputs={
                "Parent": self.rig.label,
            },
            options={
                "Sub Nodes": [
                    "skeleton",
                    "controls",
                    "geometry",
                    "guides",
                    "constraints",
                ]
            },
            parent=construction_org
        )

        self.rig.add_component(
            component_type="Utility : Reparent",
            label="Parent Skeleton",
            inputs={
                "Node To Re-Parent": "",
                "New Parent": skeleton_org_name
            },
            parent=construction_org,
        )

        self.rig.add_component(
            component_type="Utility : Delete Children",
            label="Clear Control Rig",
            inputs={
                "Node": control_org_name,
            },
            parent=make_editable,
        )

        return make_editable

    def create_rig_structure(self, parent, skeleton_org_name, control_org_name):

        build_rig = self.rig.add_component(
            component_type="Stack : Execution Block",
            label="Build Control Rig",
        )

        self.rig.add_component(
            component_type="Stack : Run Execution Block",
            label="Ensure Rig Is Editable",
            parent=build_rig,
            inputs={
                "Execution Block Label": "Make Rig Editable",
            }
        )

        self.rig.add_component(
            component_type="Utility : Remove All Guides",
            label="Remove All Guides",
            parent=build_rig,
        )

        root_component = self.rig.add_component(
            component_type="Core : Global Control Root",
            label="Global SRT",
            inputs={
                "Parent": control_org_name
            },
            parent=build_rig,
        )

        post_build = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Post Build",
            parent=build_rig,
        )

        apply_shapes = self.rig.add_component(
            component_type="Utility : Apply Control Shapes",
            label="Apply Shapes",
            parent=post_build,
        )

        self.rig.add_component(
            component_type="Utility : Color Controls",
            label="Color Controls",
            parent=apply_shapes,
        )

        self.rig.add_component(
            component_type="Utility : Type Driven Show/Hide",
            label="Hide Mechanicals",
            inputs={
                "Nodes To Search Under": [control_org_name],
            },
            options={
                "Node Types to Hide": [
                    "joint",
                    "ikHandle",
                ],
            },
            parent=post_build,
        )
        layers_org = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Construct Layers",
            parent=post_build,
        )

        self.rig.add_component(
            component_type="Utility : Add Controls To Layer",
            label="Control Layer",
            parent=layers_org,
            inputs={
                "Layer Name": "Controls",
                "Root Node": "[Global SRT].[output].[Main Control]",
            }
        )

        self.rig.add_component(
            component_type="Utility : Add Children Of Type To Layer",
            label="Geometry Layer",
            parent=layers_org,
            inputs={
                "Layer Name": "Geometry",
                "Node Types": ["transform"],
                "Root Node": self.config.generate_name(
                    classification=self.config.organisational,
                    description="geometry",
                    location=self.config.middle,
                    unique=False,
                )
            }
        )

        self.rig.add_component(
            component_type="Utility : Add Children Of Type To Layer",
            label="Joint Layer",
            parent=layers_org,
            inputs={
                "Layer Name": "Joints",
                "Node Types": ["joint"],
                "Root Node": self.config.generate_name(
                    classification=self.config.organisational,
                    description="skeleton",
                    location=self.config.middle,
                    unique=False,
                )
            }
        )
        return build_rig
