import os
import mref
import json
import aniseed_toolkit

def skeleton_file_path():
    return os.path.join(
        os.path.dirname(__file__),
        "skeleton.json",
    )

class LoadFaceFile(aniseed_toolkit.Tool):


    identifier = "Load Face File"
    classification = "Rigging"
    categories = [
        "Face Component Tools",
    ]
    icon = os.path.join(os.path.dirname(__file__), "icons", "tool_icon.png")

    def run(self):
        with open(skeleton_file_path(), 'r') as f:
            skeleton_data = json.load(f)

        # -- First pass, just create the joints
        for bone_data in skeleton_data:
            bone_name = bone_data["name"] + "_" + bone_data["location"]
            mref.select([])
            mref.create("joint", name=bone_name)

        # -- Now parent and set the parent
        for bone_data in skeleton_data:
            bone_name = bone_data["name"] + "_" + bone_data["location"]
            parent_name = bone_data["parent"]

            if not mref.objExists(bone_name):
                continue

            if parent_name and mref.objExists(parent_name):
                mref.parent(bone_name, parent_name)

            mref.get(bone_name).set_matrix(bone_data["matrix"])


class SaveFaceFile(aniseed_toolkit.Tool):


    identifier = "Save Face File"
    classification = "Rigging"
    categories = [
        "Face Component Tools",
    ]
    icon = os.path.join(os.path.dirname(__file__), "icons", "tool_icon.png")

    def run(self):
        with open(skeleton_file_path(), 'r') as f:
            skeleton_data = json.load(f)

        resolved_data = []

        # -- First pass, just create the joints
        for bone_data in skeleton_data:

            # -- Look for the bone
            bone_name = bone_data["name"] + "_" + bone_data["location"]

            # -- If the bone does not exist we skip it
            if not mref.objExists(bone_name):
                continue

            bone = mref.get(bone_name)
            print(bone)
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
