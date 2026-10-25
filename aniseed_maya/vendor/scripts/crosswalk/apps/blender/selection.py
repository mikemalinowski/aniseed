import bpy
from . import items


def select(item: object or str):
    """
    This should select the given item

    Objects are looked for first. If there is no object with the given name,
    a bone with that name is looked for (in the active armature first), and
    its armature is put into pose mode with the bone selected and active.

    Args:
        item: The item or name of object (or bone) to be selected
    """
    if not isinstance(item, list):
        item_list = [item]
    else:
        item_list = item

    for item in item_list:
        name = items.get_name(item)

        # -- Bones (as returned by selected()) are looked up by name
        obj = items.get(item) if isinstance(item, (str, bpy.types.Object)) else None

        if obj is not None:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            continue

        armature = _armature_with_bone(name)
        if armature is None:
            raise RuntimeError(f"There is no object or bone called {name}")

        _select_bone(armature, name)


def selected() -> list[object]:
    """
    This should return the items which are currently selected

    When an armature is in pose or edit mode, its selected bones are what is
    selected (the active bone first), as that is what the user is selecting.
    Otherwise the selected objects are returned.

    Returns:
        A list of items which are currently selected
    """
    bones = []

    for obj in _armatures_in_bone_modes():
        active = _active_bone(obj)

        for bone in _bones(obj):
            if not _is_bone_selected(obj, bone):
                continue

            if active is not None and bone.name == active.name:
                bones.insert(0, bone)
            else:
                bones.append(bone)

    if bones:
        return bones

    return [o for o in bpy.context.view_layer.objects if o.select_get()]


def _armatures_in_bone_modes() -> list:
    """
    Returns the selected armatures in pose or edit mode, the active one
    first.
    """
    view_layer = bpy.context.view_layer
    active = view_layer.objects.active

    armatures = [
        obj for obj in view_layer.objects
        if obj.type == "ARMATURE" and obj.mode in ("POSE", "EDIT") and (obj.select_get() or obj == active)
    ]
    armatures.sort(key=lambda obj: obj != active)
    return armatures


def _bones(armature) -> list:
    """
    Returns the armature's edit bones in edit mode, otherwise its pose bones.
    """
    if armature.mode == "EDIT":
        return list(armature.data.edit_bones)
    return list(armature.pose.bones)


def _active_bone(armature):
    if armature.mode == "EDIT":
        return armature.data.edit_bones.active
    return armature.data.bones.active


def _is_bone_selected(armature, bone) -> bool:
    if armature.mode == "EDIT":
        return bone.select

    # -- Blender 5 moved bone selection outside of edit mode from the bone
    # -- to the pose bone
    if hasattr(bone, "select"):
        return bone.select
    return bone.bone.select


def _set_bone_selected(armature, name: str):
    if armature.mode == "EDIT":
        bone = armature.data.edit_bones[name]
        bone.select = bone.select_head = bone.select_tail = True
        armature.data.edit_bones.active = bone
        return

    pose_bone = armature.pose.bones[name]
    if hasattr(pose_bone, "select"):
        pose_bone.select = True
    else:
        pose_bone.bone.select = True
    armature.data.bones.active = armature.data.bones[name]


def _armature_with_bone(name: str):
    """
    Returns the armature holding a bone with the given name, preferring the
    active object, or None.
    """
    view_layer = bpy.context.view_layer
    active = view_layer.objects.active

    candidates = [obj for obj in view_layer.objects if obj.type == "ARMATURE"]
    candidates.sort(key=lambda obj: obj != active)

    for obj in candidates:
        if name in obj.data.bones or (obj.mode == "EDIT" and name in obj.data.edit_bones):
            return obj

    return None


def _select_bone(armature, name: str):
    """
    Selects the bone, putting its armature into pose mode first unless it is
    already in pose or edit mode.
    """
    view_layer = bpy.context.view_layer

    armature.hide_set(False)
    armature.select_set(True)

    if armature.mode not in ("POSE", "EDIT"):
        # -- mode_set acts on the active object, so leave whatever mode the
        # -- current active object is in first
        current = view_layer.objects.active
        if current is not None and current != armature and current.mode != "OBJECT":
            with bpy.context.temp_override(active_object=current, object=current):
                bpy.ops.object.mode_set(mode="OBJECT")

        view_layer.objects.active = armature
        with bpy.context.temp_override(active_object=armature, object=armature):
            bpy.ops.object.mode_set(mode="POSE")

    view_layer.objects.active = armature
    _set_bone_selected(armature, name)
