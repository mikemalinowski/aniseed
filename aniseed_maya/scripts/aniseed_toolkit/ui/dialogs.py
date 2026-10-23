"""
User dialogs, and versions of library functions which ask the user for any
information they are not given. The library itself never prompts - these are
for tools and for code which explicitly wants interaction.
"""
import logging

from maya import cmds
import qtility
import scribble

from ..scene import hierarchy_io
from ..scene import mirror

log = logging.getLogger(__name__)


def ask_for_mirror_plane() -> str or None:
    """
    Asks the user which axis to mirror across.

    Returns:
        The mirror plane ("XY", "YZ" or "XZ"), or None if cancelled
    """
    mirror_plane = qtility.request.item(
        title="Mirroring",
        message="Please select the axis you want to mirror across",
        items=sorted(
            mirror.MIRROR_PLANES.keys(),
        ),
        editable=False,
    )

    if not mirror_plane:
        return None

    return mirror.MIRROR_PLANES[mirror_plane]


def ask_for_rename_data() -> list[str] or None:
    """
    Asks the user for an (optional) "replace_this:with_this" expression,
    remembering the last expression given.

    Returns:
        A [replace_this, with_this] list, or None if nothing (or something
        invalid) was given
    """
    user_data = scribble.get("mirror_across_options")

    replacement_data = qtility.request.text(
        title="Mirroring",
        message=(
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

    if not replacement_data:
        return None

    if ":" not in replacement_data:
        qtility.request.message(
            title="Mirroring",
            message="Could not resolve the remapping format",
        )
        return None

    # -- Store the users expression so they do not always
    # -- have to retype it
    user_data["mirror_expression"] = replacement_data
    user_data.save()

    return [
        replacement_data.split(":")[0],
        replacement_data.split(":")[1],
    ]


def ask_for_filepath(title: str, save: bool) -> str or None:
    """
    Asks the user for a json filepath.

    Args:
        title: The title of the dialog
        save: True when the file is to be written, False when read

    Returns:
        The chosen filepath, or None if cancelled
    """
    return qtility.request.filepath(
        title=title,
        filter_="*.json (*.json)",
        save=save,
        parent=None,
    ) or None


def global_mirror(
    transforms: list[str] or str = None,
    across: str = "YZ",
    behaviour: bool = True,
    rotate_flip: bool = False,
    name_replacement: list = None,
):
    """
    Mirrors transforms across a plane (see scene.mirror.mirror_transforms),
    asking the user for the plane if none is given, and for a name
    replacement if name_replacement is None.

    Args:
        transforms: The transforms to mirror (the selection if not given)
        across: The plane to mirror across (XY, YZ or XZ)
        behaviour: If true, the rotational behaviour is mirrored too
        rotate_flip: If true, the result is flipped 180 degrees in X and Y
        name_replacement: A [replace_this, with_this] pair used to find the
            node to apply each mirrored transform to
    """
    across = across or ask_for_mirror_plane()

    if not across:
        return

    if name_replacement is None:
        name_replacement = ask_for_rename_data()

    mirror.mirror_transforms(
        transforms=transforms,
        across=across,
        behaviour=behaviour,
        rotate_flip=rotate_flip,
        name_replacement=name_replacement,
    )


def write_hierarchy_file(nodes: list[str] = None, filepath: str = None) -> None:
    """
    Serialises the given nodes (or the selection) to a json file, asking the
    user for the filepath if one is not given.

    Args:
        nodes: List of nodes to serialise
        filepath: The filepath to save the json file

    Returns:
        None
    """
    if not nodes:
        if not cmds.ls(selection=True):
            return

        nodes = cmds.ls(selection=True)

    filepath = filepath or ask_for_filepath("Save Joint File", save=True)

    if not filepath:
        return

    hierarchy_io.write_hierarchy_file(nodes, filepath)


def load_hierarchy_file(
        root_parent: str = "",
        filepath: str = "",
        apply_names=True,
        invert=False,
        worldspace_root=False,
):
    """
    Builds the hierarchy stored in a json file (see
    scene.hierarchy_io.load_hierarchy_file), using the selection as the parent
    and asking the user for the filepath if they are not given.

    Returns:
        Dictionary where the key is the name as defined in the data and the value
        is the created node
    """
    if not root_parent:
        try:
            root_parent = cmds.ls(selection=True)[0]

        except IndexError:
            log.warning("Select (or give) the node to load the hierarchy under")
            return

    filepath = filepath or ask_for_filepath("Load Joint File", save=False)

    # -- The user cancelled the file dialog
    if not filepath:
        return

    return hierarchy_io.load_hierarchy_file(
        root_parent=root_parent,
        filepath=filepath,
        apply_names=apply_names,
        invert=invert,
        worldspace_root=worldspace_root,
    )
