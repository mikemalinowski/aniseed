"""
Provides the "Dev Example : Save Scene Version" component, which saves the
scene as the next numbered version in a folder, such as giraffe_v004.ma.

What this example teaches:
    * A "publishing" component: one which manages files rather than nodes
    * Never overwriting a file the user may want to keep
    * Passing a file path to later components through an output

Place this at the end of a build, so it saves the finished rig.

Read next: ex17_publish_rig.py
"""
import os
import re
import sys
import typing
import logging
import subprocess

# -- maya.cmds is used to save the scene
from maya import cmds

import aniseed

from aniseed_maya_dev_examples.widgets import FolderSelector

log = logging.getLogger(__name__)


class SaveSceneVersion(aniseed.RigComponent):
    """
    Saves the scene into the Output Folder as the next version, such as
    giraffe_v004.ma. Existing versions are never overwritten. Note that the
    scene is renamed to the new version, as with File > Increment and Save.
    """

    identifier = "Dev Example : Save Scene Version"

    # -- The file extension for each file type Maya can save
    EXTENSIONS = {
        "mayaAscii": "ma",
        "mayaBinary": "mb",
    }

    def __init__(self, *args, **kwargs):
        """
        Declares the Output Folder, Base Name and File Type options, and the
        Saved Path output.
        """
        super().__init__(*args, **kwargs)

        self.declare_option(
            name="Output Folder",
            value="",
            description="The folder to save the versions into. It is created if it does not exist.",
            group="Files",
            pre_expose=True,
        )

        self.declare_option(
            name="Base Name",
            value="",
            description="The start of each file name. If empty, the rig's name is used.",
            group="Files",
        )

        self.declare_option(
            name="File Type",
            value="mayaAscii",
            description="mayaAscii (.ma) or mayaBinary (.mb)",
            group="Files",
        )

        self.declare_output(
            name="Saved Path",
            description="The path of the file this build saved",
            is_default=True,
        )

    def option_widget(self, option_name):
        """
        Returns a folder selector for Output Folder and a drop down for File
        Type.
        """
        if option_name == "Output Folder":
            return FolderSelector(title="Choose Output Folder")

        if option_name == "File Type":
            return aniseed.widgets.ItemSelector(
                items=list(self.EXTENSIONS),
                default_item=self.option("File Type").get(),
            )

        return None

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Adds an "Open Output Folder" menu entry.
        """
        return {
            "Open Output Folder": self.open_output_folder,
        }

    def is_valid(self) -> bool:
        """
        Checks an output folder has been given, that it is not a file, and
        that the file type is one Maya can save.
        """
        folder = self.option("Output Folder").get()

        if not folder:
            log.warning(f"{self.label()} : no Output Folder has been given")
            return False

        if os.path.isfile(folder):
            log.warning(f"{self.label()} : the Output Folder {folder!r} is a file")
            return False

        if self.option("File Type").get() not in self.EXTENSIONS:
            log.warning(f"{self.label()} : File Type must be one of {list(self.EXTENSIONS)}")
            return False

        return True

    def run(self):
        """
        Saves the scene as the next version in the output folder.
        """
        folder = self.option("Output Folder").get()
        file_type = self.option("File Type").get()

        # -- Note that is_valid only checked the folder. Creating it is a
        # -- change to the disk, so it happens here in run, never in is_valid.
        os.makedirs(folder, exist_ok=True)

        path = next_version_path(
            folder=folder,
            base_name=self.option("Base Name").get() or self.rig.label,
            extension=self.EXTENSIONS[file_type],
        )

        # -- Key idea: the version number always goes up, so a save never
        # -- replaces a file someone might still need. Renaming then saving
        # -- is the same as File > Save Scene As.
        cmds.file(rename=path)
        cmds.file(save=True, type=file_type)

        self.output("Saved Path").set(path)
        log.info(f"{self.label()} : saved {path}")

        return True

    def open_output_folder(self):
        """
        Opens the output folder in the operating system's file browser.
        """
        folder = self.option("Output Folder").get()

        if not folder or not os.path.isdir(folder):
            log.warning(f"{self.label()} : the Output Folder {folder!r} does not exist yet")
            return

        if sys.platform == "win32":
            os.startfile(folder)

        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])

        else:
            subprocess.Popen(["xdg-open", folder])


def next_version_path(folder: str, base_name: str, extension: str) -> str:
    """
    Returns the path of the next free version of base_name in the folder,
    such as folder/giraffe_v004.ma when giraffe_v003.ma is the highest version
    there. The first version is v001.

    Args:
        folder: The folder holding the versions.
        base_name: The start of each file name.
        extension: The file extension, without the dot.
    """
    # -- Keep names safe for any file system
    base_name = re.sub(r"[^A-Za-z0-9_\-]", "_", base_name)

    pattern = re.compile(rf"^{re.escape(base_name)}_v(\d{{3,}})\.{re.escape(extension)}$")

    versions = [
        int(match.group(1))
        for match in (pattern.match(file_name) for file_name in os.listdir(folder))
        if match
    ]

    next_version = max(versions, default=0) + 1
    return os.path.join(folder, f"{base_name}_v{next_version:03d}.{extension}")
