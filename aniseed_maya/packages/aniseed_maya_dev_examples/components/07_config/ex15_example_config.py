"""
Provides the "Rig Configuration : Dev Example" configuration, which names
nodes in the form location_classification_description_## (for example
md_jnt_chain_01), and sets up a small playground stack of dev example
components when a new rig is created with it.

What this example teaches:
    * Writing a rig configuration: tokens, generate_name and extract_*
    * Setting up a default stack for new rigs with create_default_stack

Read next: ../08_publish/ex16_save_scene_version.py
"""
import re
import logging

# -- maya.cmds is used to check names are unique and to create the guides
from maya import cmds

import aniseed
from aniseed.config import NamingConventionError

log = logging.getLogger(__name__)


class DevExampleConfig(aniseed.RigConfiguration):
    """
    Names nodes in the form location_classification_description_##, for
    example md_jnt_chain_01. New rigs start with a joint chain and a control
    built from two guides.
    """

    # -- Key idea: every rig needs exactly one configuration, and the rig
    # -- finds it by looking for a component whose identifier starts with
    # -- "Rig Configuration". That is why this identifier does not start with
    # -- "Dev Example : " like the rest of this package. A rig with no
    # -- configuration refuses to build.
    identifier = "Rig Configuration : Dev Example"

    # -- Components never hard code these tokens. They ask the configuration,
    # -- such as self.config.joint or self.config.left, so a rig can switch to
    # -- another naming convention just by changing its configuration.

    # -- Locations
    left = "lf"
    right = "rt"
    middle = "md"
    front = "ft"
    back = "bk"

    # -- Classifications
    organisational = "org"
    control = "ctl"
    joint = "jnt"
    zero = "zro"
    offset = "off"
    mechanical = "mch"

    # -- A configuration can add tokens of its own. Only components which
    # -- know about this configuration can rely on them.
    guide = "gde"

    def generate_name(
            self,
            classification: str,
            description: str,
            location: str,
            counter: int = 1,
            unique: bool = True,
    ) -> str:
        """
        Returns a name in the form location_classification_description_##.

        The description is made camelCase, so it always fills a single part
        of the name ("chain start" and "chain_start" both become chainStart).

        Args:
            classification: The classification token, or the name of one of
                this configuration's tokens (such as "joint").
            description: What the node is.
            location: The location token, or the name of one of this
                configuration's tokens (such as "left").
            counter: The number to start counting from.
            unique: If True, the counter is increased until the name is not
                already used in the scene.
        """
        # -- Accept either a token ("jnt") or the name of one ("joint")
        location = getattr(self, location, location)
        classification = getattr(self, classification, classification)

        words = [word for word in re.split(r"[\s_]+", description) if word]
        if not words:
            log.warning(f"No description given for a {classification} name, using 'unnamed'")
            words = ["unnamed"]

        formatted_description = words[0][0].lower() + words[0][1:] + "".join(
            word[0].upper() + word[1:] for word in words[1:]
        )

        while True:
            name = f"{location}_{classification}_{formatted_description}_{counter:02d}"

            if not unique or not cmds.objExists(name):
                return name

            counter += 1

    # -- The extract functions reverse generate_name. Tools such as mirroring
    # -- use them to work out what a node is from its name, so they must
    # -- agree with generate_name exactly.

    def extract_location(self, name: str) -> str:
        """
        Returns the location token, the first part of the name.
        """
        return self._parts(name)[0]

    def extract_classification(self, name: str) -> str:
        """
        Returns the classification token, the second part of the name.
        """
        return self._parts(name)[1]

    def extract_description(self, name: str) -> str:
        """
        Returns the description, the third part of the name.
        """
        return self._parts(name)[2]

    def extract_counter(self, name: str) -> int:
        """
        Returns the counter, the last part of the name, as an integer.
        """
        try:
            return int(self._parts(name)[3])

        except ValueError as exc:
            raise NamingConventionError(f"Could not extract counter from {name!r}") from exc

    @staticmethod
    def _parts(name: str):
        """
        Splits a name into its four parts, raising NamingConventionError if it
        does not have exactly four.
        """
        # -- Ignore any DAG path, so "|a|md_jnt_chain_01" still works
        parts = name.split("|")[-1].split("_")

        if len(parts) != 4:
            raise NamingConventionError(
                f"{name!r} is not in the form location_classification_description_##"
            )

        return parts

    def create_default_stack(self):
        """
        Called when this configuration is the first component added to a new
        rig. Creates the rig's top level groups and two guides, and adds a
        "Build Rig" block which clears the previous build, then builds a joint
        chain along the guides and a control to drive it. The rig is then
        built, so the user sees the result straight away.
        """
        # -- aniseed.RigConfiguration.on_enter_stack calls this when the
        # -- configuration is the only component in the stack. The base class
        # -- version adds standard components, so this replaces it with dev
        # -- example ones.

        # -- The rig's label is the name of the rig node in the scene
        rig_node = self.rig.label

        guides_org = self._create_group("guides", rig_node)
        skeleton_org = self._create_group("skeleton", rig_node)
        controls_org = self._create_group("controls", rig_node)

        start_guide = self._create_guide("chain_start", guides_org, (0, 10, 0))
        end_guide = self._create_guide("chain_end", guides_org, (10, 10, 0))

        build_block = self.rig.add_component(
            component_type="Stack : Execution Block",
            label="Build Rig",
        )

        # -- The joint chain and control are rebuilt every time, so the last
        # -- build's nodes are deleted first. This uses aniseed's own (not
        # -- aniseed_maya_standard's) Delete Children component.
        self.rig.add_component(
            component_type="Utility : Delete Children",
            label="Clear Skeleton",
            inputs={"Node": skeleton_org},
            parent=build_block,
        )
        self.rig.add_component(
            component_type="Utility : Delete Children",
            label="Clear Controls",
            inputs={"Node": controls_org},
            parent=build_block,
        )

        self.rig.add_component(
            component_type="Dev Example : Joint Chain (cmds)",
            label="Joint Chain",
            inputs={
                "Start": start_guide,
                "End": end_guide,
                "Parent": skeleton_org,
            },
            parent=build_block,
        )

        self.rig.add_component(
            component_type="Dev Example : Simple Control",
            label="Chain Control",
            inputs={
                "Parent": controls_org,
                "Joint to Drive": "[Joint Chain].[output].[Root Joint]",
            },
            options={"Description": "chain"},
            parent=build_block,
        )

        self.rig.build(build_below=build_block)

        # -- Select the guides, so the user can move them and build again
        cmds.select([start_guide, end_guide], replace=True)

    def _create_group(self, description: str, parent: str) -> str:
        """
        Returns the name of the organisational group with the given
        description under the parent, creating it if it does not exist.
        """
        name = self.generate_name(self.organisational, description, self.middle, unique=False)

        if not cmds.objExists(name):
            cmds.createNode("transform", name=name, parent=parent)

        return name

    def _create_guide(self, description: str, parent: str, position) -> str:
        """
        Returns the name of the guide with the given description, creating it
        at the given position if it does not exist. Guides are locators, so
        they are easy to see and select.
        """
        name = self.generate_name(self.guide, description, self.middle, unique=False)

        if not cmds.objExists(name):
            locator = cmds.spaceLocator(name=name)[0]
            cmds.parent(locator, parent)
            cmds.xform(name, worldSpace=True, translation=position)

        return name
