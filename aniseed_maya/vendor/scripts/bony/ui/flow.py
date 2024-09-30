import qute
import scribble
import maya.cmds as mc

from .. import flip

MIRROR_PLANES = {
    "Z": 'XY',
    "X": 'YZ',
    "Y": 'XZ',
}


# --------------------------------------------------------------------------------------
def mirror_current():

    mirror_plane = qute.utilities.request.item(
        title="Mirror Current Transforms",
        label="Please select the axis you want to mirror across",
        items=sorted(
            MIRROR_PLANES.keys(),
        ),
        editable=False,
    )

    if not mirror_plane:
        return

    user_data = scribble.get("mirror_across_options")

    flip.global_mirror(
        transforms=mc.ls(sl=True),
        across=MIRROR_PLANES[mirror_plane],
    )


# --------------------------------------------------------------------------------------
def mirror_across():

    mirror_plane = qute.utilities.request.item(
        title="Mirroring",
        label="Please select the axis you want to mirror across",
        items=sorted(
            MIRROR_PLANES.keys(),
        ),
        editable=False,
    )

    if not mirror_plane:
        return

    user_data = scribble.get("mirror_across_options")

    replacement_data = qute.utilities.request.text(
        title="Mirroring",
        label=(
            "You can (optionally) provide a search and replace. \n"
            "If you do, this will mirror the selected transforms "
            "over to the objects with the replaced "
            "name. "
            "\n\n"
            "Use the format 'replace_this:with_this"
            "\n\n"
            "If you leave it blank, it will mirror the selected objects"
        ),
        text=user_data.get("mirror_expression", "")
    )

    kwargs = {}

    if replacement_data:

        if not ":" in replacement_data:
            qute.utilities.request.message(
                title="Mirroring",
                label="Could not resolve the remapping format",
            )
            return

        # -- Store the users expression so they do not always
        # -- have to retype it
        user_data["mirror_expression"] = replacement_data
        user_data.save()

        kwargs["result_remapping"] = Renamer(
            replacement_data.split(":")[0],
            replacement_data.split(":")[1],
        ).rename_this

    flip.global_mirror(
        transforms=mc.ls(sl=True),
        across=MIRROR_PLANES[mirror_plane],
        **kwargs
    )

class Renamer:

    def __init__(self, from_this, to_this):
        self.from_this = from_this
        self.to_this = to_this

    def rename_this(self, node):
        return node.replace(self.from_this, self.to_this)

def _name_replacement_function(node, replace_this, with_this):
    return node.replace(replace_this, with_this)
