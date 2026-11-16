import typing
import logging
import crosswalk

from . import component

log = logging.getLogger(__name__)


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

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Exposes Update, which adds any component of the default stack that
        is missing from the rig.
        """
        menu = super().user_functions()
        menu["Update"] = self.user_func_update
        return menu

    def user_func_update(self) -> list:
        """
        Adds any component the default stack would create which the rig does
        not have, in the position the default stack would put it. Existing
        components are found by label and type and are left untouched, so a
        component which has been renamed is added again.

        Returns:
            The components which were added
        """
        added_components = self._ensure_default_stack()

        if added_components:
            log.info(f"Added: {', '.join(added.label() for added in added_components)}")
        else:
            log.info("The rig already has every default component")

        return added_components

    def _ensure_default_stack(self, unique_org_names: bool = False) -> list:
        """
        Creates every component of the default stack which is missing, then
        points the added components which need the skeleton root joint at
        the joint the Global SRT drives.

        Args:
            unique_org_names: If True the control and skeleton org names are
                made unique to the scene. A new stack wants this, whereas an
                update wants the names of the orgs which already exist.

        Returns:
            The components which were added
        """
        control_org_name = self.generate_name(
            classification=self.organisational,
            description="controls",
            location=self.middle,
            unique=unique_org_names,
        )

        skeleton_org_name = self.generate_name(
            classification=self.organisational,
            description="skeleton",
            location=self.middle,
            unique=unique_org_names,
        )

        # -- These track, per parent, the last component placed, so that a
        # -- missing component is inserted after its predecessor
        self._previous_siblings = dict()
        self._added_components = []

        self.create_editable_structure(None, skeleton_org_name, control_org_name)
        self.create_rig_structure(None, skeleton_org_name, control_org_name)

        added_components = self._added_components
        self._link_skeleton_root(added_components)
        return added_components

    def _ensure_component(
            self,
            component_type: str,
            label: str,
            inputs: typing.Dict = None,
            options: typing.Dict = None,
            parent: "component.RigComponent" = None,
            after: "component.RigComponent" = None,
    ) -> typing.Optional["component.RigComponent"]:
        """
        Returns the component with the given label and type, adding it (with
        the given inputs and options) if the rig does not have one. An added
        component is placed after the component last ensured under the same
        parent (and after the branch holding the after component, if given),
        or straight after this config at the root.
        """
        parent_key = parent.uuid() if parent else None

        existing = self.rig.get_component_by_label(label, of_type=component_type)
        if existing:
            # -- An existing component may sit deeper than the parent (such
            # -- as Clear Control Rig under Store Shapes in older rigs), so
            # -- what follows it is placed after its branch under the parent
            branch = self._branch_under(existing, parent)
            if branch:
                self._previous_siblings[parent_key] = branch
            return existing

        anchors = [
            self._previous_siblings.get(parent_key),
            self._branch_under(after, parent) if after else None,
        ]
        anchors = [anchor for anchor in anchors if anchor]

        if anchors:
            child_index = max(anchor.child_index() for anchor in anchors) + 1
        elif parent is None:
            child_index = self.child_index() + 1
        else:
            child_index = 0

        added = self.rig.add_component(
            component_type=component_type,
            label=label,
            inputs=inputs,
            options=options,
            parent=parent,
            child_index=child_index,
        )

        if added:
            self._previous_siblings[parent_key] = added
            self._added_components.append(added)

        return added

    @staticmethod
    def _branch_under(
            rig_component: "component.RigComponent",
            parent: "component.RigComponent",
    ) -> typing.Optional["component.RigComponent"]:
        """
        Returns the component, or its ancestor, which sits directly under
        parent (or at the root if parent is None). None if it is not under
        parent at all.
        """
        while rig_component is not None and rig_component.parent is not parent:
            rig_component = rig_component.parent
        return rig_component

    def _link_skeleton_root(self, components: list) -> None:
        """
        Points the given Parent Skeleton and Push Rotations To Orients
        components at the joint the Global SRT drives. The push needs a
        joint to start from, so without one it is removed.
        """
        srt_component = self.rig.get_component_by_label("Global SRT")
        root_joint = srt_component.input("Joint To Drive").get() if srt_component else ""

        for linked_component in components:

            if linked_component.label() == "Parent Skeleton":
                linked_component.input("Node To Re-Parent").set(root_joint)

            if linked_component.label() == "Push Rotations To Orients":
                if root_joint:
                    linked_component.input("Chain Root").set(root_joint)
                else:
                    self.rig.remove_component(linked_component)

    def create_default_stack(self):

        self._ensure_default_stack(unique_org_names=True)

        edit_component = self.rig.get_component_by_label("Make Rig Editable")
        srt_component = self.rig.get_component_by_label("Global SRT")
        created_joint = srt_component.input("Joint To Drive").get()

        self.stack.build()
        self.stack.build(build_below=edit_component)

        # -- Finally select the root joint for the user
        crosswalk.selection.select(created_joint)
        return

    def create_editable_structure(self, parent, skeleton_org_name, control_org_name):

        make_editable = self._ensure_component(
            component_type="Stack : Execution Block",
            label="Make Rig Editable",
        )

        # -- Clear the control rig before the rig hierarchy is ensured. Deleting
        # -- the controls deletes the constraints which target them, and Maya then
        # -- deletes any group left empty by that (such as the constraints group).
        # -- Ensuring the hierarchy afterwards recreates anything removed this way.
        clear_control_rig = self._ensure_component(
            component_type="Utility : Delete Children",
            label="Clear Control Rig",
            inputs={
                "Node": control_org_name,
            },
            parent=make_editable,
        )

        construction_org = self._ensure_component(
            component_type="Stack : Organiser",
            label="Rig Hierarchy",
            parent=make_editable,
        )

        # -- Lets pre-load our Standard rigs with a series of components
        self._ensure_component(
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

        self._ensure_component(
            component_type="Utility : Reparent",
            label="Parent Skeleton",
            inputs={
                "Node To Re-Parent": "",
                "New Parent": skeleton_org_name
            },
            parent=construction_org,
        )

        # -- These must run once the control rig has been cleared, so the
        # -- joints are free of constraints and can be cleaned up. Pushing the
        # -- rotations while the constraints still drive the joints bakes the
        # -- posed rotations into the orients.
        self._ensure_component(
            component_type="Utility : Push Rotations To Joint Orients (Hierarchy)",
            label="Push Rotations To Orients",
            inputs={
                "Chain Root": "",
            },
            parent=make_editable,
            after=clear_control_rig,
        )

        self._ensure_component(
            component_type="Utility : Disable Segment Scale Compensation",
            label="Disable Segment Scale Compensation",
            inputs={
                "Root": skeleton_org_name,
            },
            parent=make_editable,
            after=clear_control_rig,
        )

        return make_editable

    def create_rig_structure(self, parent, skeleton_org_name, control_org_name):

        build_rig = self._ensure_component(
            component_type="Stack : Execution Block",
            label="Build Control Rig",
        )

        self._ensure_component(
            component_type="Stack : Run Execution Block",
            label="Ensure Rig Is Editable",
            parent=build_rig,
            inputs={
                "Execution Block Label": "Make Rig Editable",
            }
        )

        self._ensure_component(
            component_type="Utility : Remove All Guides",
            label="Remove All Guides",
            parent=build_rig,
        )

        root_component = self._ensure_component(
            component_type="Core : Global Control Root",
            label="Global SRT",
            inputs={
                "Parent": control_org_name
            },
            parent=build_rig,
        )

        post_build = self._ensure_component(
            component_type="Stack : Organiser",
            label="Post Build",
            parent=build_rig,
        )

        apply_shapes = self._ensure_component(
            component_type="Utility : Apply Control Shapes",
            label="Apply Shapes",
            parent=post_build,
        )

        self._ensure_component(
            component_type="Utility : Color Controls",
            label="Color Controls",
            parent=apply_shapes,
        )

        self._ensure_component(
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
        layers_org = self._ensure_component(
            component_type="Stack : Organiser",
            label="Construct Layers",
            parent=post_build,
        )

        self._ensure_component(
            component_type="Utility : Add Controls To Layer",
            label="Control Layer",
            parent=layers_org,
            inputs={
                "Layer Name": "Controls",
                "Root Node": "[Global SRT].[output].[Main Control]",
            }
        )

        self._ensure_component(
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

        self._ensure_component(
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
