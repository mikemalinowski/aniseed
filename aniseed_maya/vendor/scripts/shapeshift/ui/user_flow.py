import qute
import scribble
import maya.cmds as mc

from .. import core
from .. import mirror
from .. import library
from .. import constants


# --------------------------------------------------------------------------------------
def apply_from_library():

    shape = qute.utilities.request.item(
        title="Apply Shape",
        label="Please select the shape to apply",
        items=library.shape_library(),
        editable=False,
    )

    if not shape:
        return

    for node in mc.ls(sl=True):
        core.apply(
            node,
            data=shape,
        )


# --------------------------------------------------------------------------------------
def apply_file():

    shape = qute.utilities.request.filepath(
        title="Select Shape File",
        filter_="*.json (*.json)",
        path=constants.SEARCH_PATHS[0],
        save=False,
    )

    if not shape:
        return

    for node in mc.ls(sl=True):
        core.apply(
            node,
            data=shape,
        )

# --------------------------------------------------------------------------------------
def rotate():

    data = dict(
        x=0,
        y=0,
        z=0,
    )

    for key in data:

        value = qute.utilities.request.text(
            title="Rotate Shape",
            label=(
                f"Please give the {key} rotation value"
            ),
        )

        if not value:
            return

        data[key] = float(value)

    for node in mc.ls(sl=True):
        core.rotate_shape(
            node,
            **data
        )


# --------------------------------------------------------------------------------------
def scale():

    value = qute.utilities.request.text(
        title="Scale Shape",
        label=(
            f"Please give a scale value"
        ),
        text="1",
    )

    if not value:
        return

    for node in mc.ls(sl=True):
        core.scale(
            node,
            float(value),
        )


# --------------------------------------------------------------------------------------
def mirror_shapes_across():

    mirror_plane = qute.utilities.request.item(
        title="Mirroring",
        label="Please select the axis you want to mirror across",
        items=["X", "Y", "Z"],
        editable=False,
    )

    if not mirror_plane:
        return

    user_data = scribble.get("mirror_shape_across_options")

    replacement_data = qute.utilities.request.text(
        title="Mirroring",
        label=(
            "Please provide the text replacement to map from one side "
            "to another"
        ),
        text=user_data.get("mirror_expression", "_LF:_RT")
    )

    kwargs = {}

    if not replacement_data:
        return

    if not ":" in replacement_data:
        qute.utilities.request.message(
            title="Mirroring",
            label="Could not resolve the remapping format",
        )
        return

    search_for = replacement_data.split(":")[0]
    replace_with = replacement_data.split(":")[1]

    # -- Store the users expression so they do not always
    # -- have to retype it
    user_data["mirror_expression"] = replacement_data
    user_data.save()

    for node in mc.ls(sl=True)[:]:

        opposing_node = node.replace(search_for, replace_with)

        if not mc.objExists(opposing_node):
            print(f"{opposing_node} does not exist. Cannot mirror curve")
            continue

        mirror.mirror_across(
            from_node=node,
            to_node=opposing_node,
            axis=mirror_plane,
        )

