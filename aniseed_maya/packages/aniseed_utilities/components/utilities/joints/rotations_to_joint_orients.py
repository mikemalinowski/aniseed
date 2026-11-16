import os
import logging
import mref
import aniseed
import aniseed_utilities as au

log = logging.getLogger(__name__)


class PushRotationsToJointOrientsHierarchy(aniseed.RigComponent):

    identifier = "Utility : Push Rotations To Joint Orients (Hierarchy)"
    icon = os.path.join(os.path.dirname(__file__), "push_rotations_to_joint_orients_hierarchy.png")
    deprecated_names = ["Push Rotations To Joint Orients (Hierarchy)"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            "Chain Root",
            value="",
            description="Chain Root",
        )

    def input_widget(self, requirement_name: str):
        return aniseed.widgets.ObjectSelector()

    def run(self) -> bool:
        # -- Checked here rather than in is_valid, as the root may be created
        # -- earlier in the same build
        chain_root_name = self.input("Chain Root").get()

        if not chain_root_name or not mref.objExists(chain_root_name):
            log.warning(f"{self.label()}: The Chain Root input ({chain_root_name!r}) is not an existing node")
            return False

        chain_root: mref.types.JointNode = mref.get(chain_root_name)
        chain_children = chain_root.children(
            node_type="joint",
            recursive=True,
        )

        au.scene.joints.move_rotations_to_orients(
            [
                joint.name()
                for joint in [chain_root] + chain_children
            ]
        )


class PushRotationsToJointOrients(aniseed.RigComponent):
    identifier = "Utility : Push Rotations To Joint Orients (List)"
    icon = os.path.join(os.path.dirname(__file__), "push_rotations_to_joint_orients_list.png")
    deprecated_names = ["Push Rotations To Joint Orients (List)"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.declare_input(
            "Joints",
            value="",
            description="All Joints to be affected",
        )

    def input_widget(self, requirement_name: str):
        return aniseed.widgets.ObjectList()

    def run(self):
        au.scene.joints.move_rotations_to_orients(self.input("Joints").get())

