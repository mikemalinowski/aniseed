"""
Registers the "Load Face File" and "Save Face File" aniseed_toolkit tools,
which create the face skeleton joints from skeleton.json and write the scene
joints' parents and matrices back into that file. Saving drops any bones which
are not present in the scene.
"""
import os
import mref
import json
import aniseed_toolkit


def skeleton_file_path():
    """
    Returns the path to the face skeleton json file
    """
    return os.path.join(
        os.path.dirname(__file__),
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


class LoadFaceFile(aniseed_toolkit.Tool):

    identifier = "Load Face File"
    classification = "Rigging"
    categories = [
        "Face Component Tools",
    ]
    icon = os.path.join(os.path.dirname(__file__), "icons", "tool_icon.png")

    def run(self):
        """
        Creates a joint for every bone in the face skeleton json file, then
        parents each one (where its parent exists) and applies its stored
        matrix.
        """
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


class SaveFaceFile(aniseed_toolkit.Tool):

    identifier = "Save Face File"
    classification = "Rigging"
    categories = [
        "Face Component Tools",
    ]
    icon = os.path.join(os.path.dirname(__file__), "icons", "tool_icon.png")

    def run(self):
        """
        Writes the parent and matrix of each face bone found in the scene back
        into the face skeleton json file. Bones which do not exist in the scene
        are dropped from the file.
        """
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


# -- Register our tools
aniseed_toolkit.register(LoadFaceFile)
aniseed_toolkit.register(SaveFaceFile)
aniseed_toolkit.register_resource_path(os.path.dirname(__file__))
