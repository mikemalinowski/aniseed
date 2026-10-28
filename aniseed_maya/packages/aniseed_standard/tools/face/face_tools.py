"""
The "Load Face File" and "Save Face File" Rigging Toolkit tools, which create
the face skeleton joints from the face component's skeleton.json and write the
scene joints' parents and matrices back into that file. Saving drops any bones
which are not present in the scene.

The Rigging Toolkit finds these tools because they are in the tools folder of
the aniseed_standard package.
"""
import os
import json
import logging

import mref

from aniseed import toolkits

log = logging.getLogger(__name__)

# -- The icon both tools show with
_ICON = os.path.join(os.path.dirname(__file__), "icons", "tool_icon.png")


def skeleton_file_path():
    """
    Returns the path to the face skeleton json file, which lives alongside
    the face component
    """
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "components",
        "limbs",
        "face",
        "skeleton.json",
    )


def load_skeleton_data():
    """
    Returns the list of bone data stored in the face skeleton json file
    """
    with open(skeleton_file_path(), 'r') as f:
        return json.load(f)


def bone_label(bone_data):
    """
    Returns the label (and node name) of the given bone data
    """
    return bone_data["name"] + "_" + bone_data["location"]


def _requires_skeleton_file() -> bool:
    if not os.path.isfile(skeleton_file_path()):
        log.warning(f"The face skeleton file does not exist : {skeleton_file_path()}")
        return False

    return True


# --------------------------------------------------------------------------------------
class LoadFaceFile(toolkits.Tool):
    """
    Creates the face skeleton joints stored in the face component's
    skeleton.json: a joint for every bone, parented (where its parent
    exists) and placed with its stored matrix.
    """

    identifier = "Load Face File"
    toolkit = "Rigging"
    categories = ["Face Component Tools"]
    icon = _ICON

    def is_valid(self) -> bool:
        return _requires_skeleton_file()

    def run(self) -> None:
        skeleton_data = load_skeleton_data()

        # -- First pass, just create the joints
        for bone_data in skeleton_data:
            mref.create("joint", name=bone_label(bone_data))

        # -- Now set the parent and the transform
        for bone_data in skeleton_data:
            bone_name = bone_label(bone_data)
            parent_name = bone_data["parent"]

            if not mref.objExists(bone_name):
                continue

            bone = mref.get(bone_name)

            if parent_name and mref.objExists(parent_name):
                bone.set_parent(parent_name)

            bone.set_matrix(bone_data["matrix"])


# --------------------------------------------------------------------------------------
class SaveFaceFile(toolkits.Tool):
    """
    Writes the parent and matrix of each face bone in the scene back into the
    face component's skeleton.json. Bones which do not exist in the scene are
    dropped from the file.
    """

    identifier = "Save Face File"
    toolkit = "Rigging"
    categories = ["Face Component Tools"]
    icon = _ICON

    def is_valid(self) -> bool:
        if not _requires_skeleton_file():
            return False

        # -- Bones missing from the scene are dropped from the file, so with
        # -- none in the scene the whole skeleton would be erased
        if not any(mref.objExists(bone_label(bone_data)) for bone_data in load_skeleton_data()):
            log.warning("None of the face bones are in the scene (use Load Face File first)")
            return False

        return True

    def run(self) -> None:
        resolved_data = []

        for bone_data in load_skeleton_data():

            # -- Look for the bone. If it does not exist we skip it
            bone_name = bone_label(bone_data)
            if not mref.objExists(bone_name):
                continue

            bone = mref.get(bone_name)

            # -- If we have a parent, store it
            if bone.parent():
                bone_data["parent"] = bone.parent().name()

            bone_data["matrix"] = bone.get_matrix()
            resolved_data.append(bone_data)

        with open(skeleton_file_path(), 'w') as f:
            json.dump(resolved_data, f, indent=4)

        log.info(f"Saved {len(resolved_data)} face bones to {skeleton_file_path()}")
