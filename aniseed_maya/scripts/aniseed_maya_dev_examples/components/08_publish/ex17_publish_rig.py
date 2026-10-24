"""
Provides the "Dev Example : Publish Rig" component, which publishes the rig
into a new numbered version folder: a copy of the work scene, the rig recipe,
an FBX of the skeleton (cleaned up for a game engine), and a manifest
describing it all. The user's own scene is never changed.

What this example teaches:
    * Running work after a successful build with on_build_finished
    * Checking the scene before publishing, and recording the results
    * Cleaning a COPY of the scene, never the user's scene
    * Doing work which re-opens the scene safely (it ends the current rig)
    * Exporting the recipe with rig.save, and an FBX with the fbxmaya plugin

Each publish creates:

    <Publish Root>/<Asset Name>/v###/
        <asset>_work.ma        the scene as it was when published
        <asset>_recipe.json    the rig recipe
        <asset>.fbx            the FBX Roots, cleaned for export
        publish.json           the manifest

Read next: ../../anti_patterns.py
"""
import os
import re
import sys
import json
import time
import typing
import getpass
import logging
import tempfile
import functools
import subprocess

# -- maya.cmds does most of the work. maya.mel is needed only because the FBX
# -- exporter's settings are MEL commands, and maya.utils lets us run work
# -- once Maya is idle.
import maya.utils
from maya import cmds
from maya import mel

import aniseed

from aniseed_maya_dev_examples.widgets import FolderSelector

log = logging.getLogger(__name__)


# -- The choices for the Publish When option
AFTER_BUILD = "After Successful Build"
DURING_BUILD = "During Build"

# -- The channels baked onto the export joints
TRANSFORM_ATTRIBUTES = [f"{attribute}{axis}" for attribute in ("translate", "rotate", "scale") for axis in "XYZ"]


class PublishRig(aniseed.RigComponent):
    """
    Publishes the rig to a new version folder under Publish Root: a copy of
    the scene, the rig recipe, an FBX of the FBX Roots and a publish.json
    manifest. Cleaning for the FBX happens on a copy, so your scene is left
    exactly as it was.
    """

    identifier = "Dev Example : Publish Rig"

    def __init__(self, *args, **kwargs):
        """
        Declares the FBX Roots and Nodes To Delete inputs, the file and
        behaviour options, and the Publish Folder and Manifest Path outputs.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="FBX Roots",
            value=[],
            validate=False,
            description="The nodes to export to FBX, along with everything beneath them. Usually the skeleton (and geometry) groups.",
            group="Export",
        )

        self.declare_input(
            name="Nodes To Delete",
            value=[],
            validate=False,
            description="Deleted from the copy before the FBX export, such as the controls group",
            group="Export",
        )

        self.declare_option(
            name="Publish Root",
            value="",
            description="The folder publishes are made in. Each asset gets a folder of versions under it.",
            group="Files",
            pre_expose=True,
        )

        self.declare_option(
            name="Asset Name",
            value="",
            description="The name of the asset. If empty, the rig's name is used.",
            group="Files",
            pre_expose=True,
        )

        self.declare_option(
            name="Save Work Scene",
            value=True,
            description="Store a copy of the scene in the publish",
            group="Files",
        )

        self.declare_option(
            name="Export Recipe",
            value=True,
            description="Store the rig recipe in the publish",
            group="Files",
        )

        self.declare_option(
            name="Export FBX",
            value=True,
            description="Export the FBX Roots to an FBX file",
            group="Export",
        )

        self.declare_option(
            name="Clean Before Export",
            value=True,
            description=(
                "Clean a copy of the scene before the FBX export: bake and remove constraints, "
                "delete Nodes To Delete, import references, remove namespaces, and delete unknown "
                "nodes and empty groups. Needs Publish When to be After Successful Build."
            ),
            group="Export",
        )

        self.declare_option(
            name="Fail On Pre-Flight Issues",
            value=False,
            description="If on, problems found by the pre-flight checks stop the publish. If off, they are only recorded.",
            group="Behaviour",
        )

        self.declare_option(
            name="Publish When",
            value=AFTER_BUILD,
            description=(
                "After Successful Build: publish once every component has built, and only if the "
                "build succeeded. During Build: publish when this component runs."
            ),
            group="Behaviour",
        )

        self.declare_output(
            name="Publish Folder",
            description="The version folder of the last publish",
            is_default=True,
        )

        self.declare_output(
            name="Manifest Path",
            description="The publish.json of the last publish",
        )

    def option_widget(self, option_name):
        """
        Returns a folder selector for Publish Root and a drop down for
        Publish When.
        """
        if option_name == "Publish Root":
            return FolderSelector(title="Choose Publish Root")

        if option_name == "Publish When":
            return aniseed.widgets.ItemSelector(
                items=[AFTER_BUILD, DURING_BUILD],
                default_item=self.option("Publish When").get(),
            )

        return None

    def input_widget(self, requirement_name):
        """
        Returns an object list for the FBX Roots and Nodes To Delete inputs.
        """
        if requirement_name in ("FBX Roots", "Nodes To Delete"):
            return aniseed.widgets.ObjectList()
        return None

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Adds menu entries to publish without building, and to open the most
        recent publish.
        """
        return {
            "Publish Now (no build)": self.publish,
            "Open Latest Publish": self.open_latest_publish,
        }

    def is_valid(self) -> bool:
        """
        Checks the publish settings make sense before anything is built.
        """
        root = self.option("Publish Root").get()

        if not root:
            log.warning(f"{self.label()} : no Publish Root has been given")
            return False

        if os.path.isfile(root):
            log.warning(f"{self.label()} : the Publish Root {root!r} is a file")
            return False

        when = self.option("Publish When").get()
        if when not in (AFTER_BUILD, DURING_BUILD):
            log.warning(f"{self.label()} : Publish When must be {AFTER_BUILD!r} or {DURING_BUILD!r}")
            return False

        exporting = self.option("Export FBX").get()
        roots_input = self.input("FBX Roots")

        if exporting and not roots_input.is_address() and not roots_input.get():
            log.warning(f"{self.label()} : Export FBX is on, but no FBX Roots have been given")
            return False

        # -- Cleaning re-opens the scene, which would destroy the rig while it
        # -- was still building (see _clean_export_and_restore)
        if exporting and self.option("Clean Before Export").get() and when == DURING_BUILD:
            log.warning(f"{self.label()} : Clean Before Export needs Publish When to be {AFTER_BUILD!r}")
            return False

        return True

    def run(self):
        """
        Publishes now if Publish When is During Build. Otherwise the publish
        waits for on_build_finished.
        """
        if self.option("Publish When").get() == DURING_BUILD:
            self.publish()

        else:
            log.info(f"{self.label()} : will publish once the build has succeeded")

        return True

    def on_build_finished(self, successful: bool) -> None:
        """
        Publishes once the whole build has finished, if it succeeded and
        Publish When is After Successful Build.
        """
        # -- Key idea: on_build_finished is called on every component in the
        # -- build, after the last one has run, and says whether the build
        # -- succeeded. Publishing here means a broken rig is never published,
        # -- and everything after this component in the stack has been built.
        # --
        # -- Note that an exception raised here cannot fail the build, which
        # -- has already finished. It is logged, so check the Script Editor if
        # -- a publish does not appear.
        if self.option("Publish When").get() != AFTER_BUILD:
            return

        if not successful:
            log.warning(f"{self.label()} : the build failed, so nothing was published")
            return

        self.publish()

    # ----------------------------------------------------------------------------------
    def publish(self):
        """
        Publishes the rig. The work scene and recipe are written straight
        away. When cleaning for the FBX, the export happens once Maya is idle,
        as it re-opens the scene (see _run_when_idle).
        """
        plan = self._make_plan()

        # -- Pre-flight checks look for problems which would make a broken
        # -- publish. They are recorded in the manifest either way.
        plan["pre_flight_issues"] = _pre_flight_checks()
        for issue in plan["pre_flight_issues"]:
            log.warning(f"{self.label()} : pre-flight : {issue}")

        if plan["pre_flight_issues"] and self.option("Fail On Pre-Flight Issues").get():
            raise RuntimeError(f"{self.label()} : the pre-flight checks found problems, so nothing was published")

        os.makedirs(plan["folder"])

        # -- aniseed writes changes to the rig node's recipe shortly after
        # -- they happen, rather than straight away. Make sure it is up to
        # -- date, as the scene copy below should include it.
        self.rig.flush_recipe()

        if self.option("Save Work Scene").get():
            _export_scene_copy(plan["work_scene"])
            plan["files"].append(plan["work_scene"])

        if self.option("Export Recipe").get():
            # -- rig.save writes the recipe as json. The Maya host adds the
            # -- rig's joints and groups to it, so loading the recipe into an
            # -- empty rig recreates them.
            self.rig.save(plan["recipe"])
            plan["files"].append(plan["recipe"])

        self.output("Publish Folder").set(plan["folder"])
        self.output("Manifest Path").set(plan["manifest"])

        if not self.option("Export FBX").get():
            _write_manifest(plan)

        elif not self.option("Clean Before Export").get():
            # -- Without cleaning, the FBX is exported straight from the
            # -- user's scene, which is left untouched
            _export_fbx(plan["fbx"], plan["fbx_roots"])
            plan["files"].append(plan["fbx"])
            _write_manifest(plan)

        else:
            # -- Cleaning works on a copy of the scene. If the work scene is
            # -- not being kept, a temporary copy is made instead.
            if not self.option("Save Work Scene").get():
                plan["snapshot"] = os.path.join(tempfile.gettempdir(), f"{plan['asset']}_publish_snapshot.ma")
                plan["snapshot_is_temporary"] = True
                _export_scene_copy(plan["snapshot"])

            # -- From here on, only the plan is used, never self. Re-opening
            # -- the scene ends this rig and this component with it.
            _run_when_idle(functools.partial(_clean_export_and_restore, plan))

        log.info(f"{self.label()} : publishing to {plan['folder']}")

    def open_latest_publish(self):
        """
        Opens the most recent version folder in the file browser.
        """
        asset_folder = os.path.join(self.option("Publish Root").get(), self._asset_name())

        versions = _existing_versions(asset_folder)
        if not versions:
            log.warning(f"{self.label()} : there are no publishes in {asset_folder!r} yet")
            return

        _open_in_file_browser(os.path.join(asset_folder, f"v{max(versions):03d}"))

    # ----------------------------------------------------------------------------------
    def _asset_name(self) -> str:
        """
        Returns the asset name, falling back to the rig's name, made safe for
        use in file names.
        """
        return re.sub(r"[^A-Za-z0-9_\-]", "_", self.option("Asset Name").get() or self.rig.label)

    def _resolved_list(self, input_name: str) -> typing.List[str]:
        """
        Returns the value of a node list input, as a list, even when it is
        wired to an output holding a single node.
        """
        value = self.input(input_name).get() or []
        return [value] if isinstance(value, str) else list(value)

    def _make_plan(self) -> dict:
        """
        Gathers everything the publish needs into a plain dictionary: the
        paths to write, the nodes to export, and the state of the user's
        scene so it can be restored.
        """
        asset = self._asset_name()
        asset_folder = os.path.join(self.option("Publish Root").get(), asset)
        version = max(_existing_versions(asset_folder), default=0) + 1
        folder = os.path.join(asset_folder, f"v{version:03d}")

        work_scene = os.path.join(folder, f"{asset}_work.ma")

        return {
            "asset": asset,
            "version": version,
            "folder": folder,
            "work_scene": work_scene,
            "recipe": os.path.join(folder, f"{asset}_recipe.json"),
            "fbx": os.path.join(folder, f"{asset}.fbx"),
            "manifest": os.path.join(folder, "publish.json"),
            # -- The copy of the scene which is cleaned, and then re-opened to
            # -- give the user their scene back
            "snapshot": work_scene,
            "snapshot_is_temporary": False,
            "fbx_roots": self._resolved_list("FBX Roots"),
            "nodes_to_delete": self._resolved_list("Nodes To Delete"),
            "original_scene": cmds.file(query=True, sceneName=True),
            "original_modified": cmds.file(query=True, modified=True),
            "rig": self.rig.label,
            "published_by": getpass.getuser(),
            "published_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "files": [],
            "cleanup_steps": [],
            "pre_flight_issues": [],
        }


# --------------------------------------------------------------------------------------
# -- The functions below work only from the plan and the scene, never from
# -- the component, so they keep working after the scene has been re-opened.
# --------------------------------------------------------------------------------------
def _run_when_idle(function: typing.Callable) -> None:
    """
    Runs the function once Maya is idle, after the build (and the app's
    response to it) has completed. In batch mode, such as mayapy, Maya is
    never idle, so the function is run straight away.

    Re-opening the scene in the middle of a build would destroy the rig while
    aniseed is still using it, which is why the cleanup waits.
    """
    if cmds.about(batch=True):
        function()

    else:
        maya.utils.executeDeferred(function)


def _clean_export_and_restore(plan: dict) -> None:
    """
    Opens the copy of the scene, cleans it, exports the FBX, then re-opens
    the copy again to give the user back their scene, and writes the
    manifest.

    Args:
        plan: The publish plan made by PublishRig._make_plan.
    """
    try:
        cmds.file(plan["snapshot"], open=True, force=True)

        plan["cleanup_steps"] = _clean_scene(plan)

        _export_fbx(plan["fbx"], plan["fbx_roots"])
        plan["files"].append(plan["fbx"])

    finally:
        # -- Key idea: whatever happens, give the user back their scene. Even
        # -- if the cleanup or export fails, they must never be left looking
        # -- at the half deleted copy.
        _restore_scene(plan)

    _write_manifest(plan)
    log.info(f"Published {plan['asset']} v{plan['version']:03d} to {plan['folder']}")


def _restore_scene(plan: dict) -> None:
    """
    Re-opens the uncleaned copy of the scene, then gives it the user's
    original file name and modified state, so saving carries on as if
    nothing had happened.

    Args:
        plan: The publish plan made by PublishRig._make_plan.
    """
    cmds.file(plan["snapshot"], open=True, force=True)

    # -- Without this, the user's next save would overwrite the published
    # -- copy rather than their own file. A scene which had never been saved
    # -- is renamed to "untitled" in the project's scenes folder.
    cmds.file(rename=plan["original_scene"] or "untitled")
    cmds.file(modified=plan["original_modified"])

    if plan["snapshot_is_temporary"]:
        os.remove(plan["snapshot"])


def _export_scene_copy(path: str) -> None:
    """
    Writes the whole scene to the given path. Unlike Save Scene As, this does
    not rename the user's scene.

    Args:
        path: The .ma file to write.
    """
    cmds.file(
        path,
        exportAll=True,
        type="mayaAscii",
        preserveReferences=True,
        force=True,
    )


def _pre_flight_checks() -> typing.List[str]:
    """
    Returns a description of each problem found in the scene which could
    spoil the publish. An empty list means no problems were found.
    """
    issues = []

    unknown_nodes = cmds.ls(type="unknown") or []
    if unknown_nodes:
        issues.append(f"{len(unknown_nodes)} unknown node(s), usually from a missing plugin")

    for reference_file in cmds.file(query=True, reference=True) or []:
        if not cmds.referenceQuery(reference_file, isLoaded=True):
            issues.append(f"the reference {reference_file} is not loaded")

    # -- cmds.ls gives the shortest unique name of each node, so a name
    # -- containing "|" means another node has the same short name. Engines
    # -- generally need every node in an FBX to have its own name.
    duplicates = [node for node in cmds.ls(dag=True) if "|" in node]
    if duplicates:
        issues.append(f"{len(duplicates)} node(s) share a short name with another node, such as {duplicates[0]}")

    return issues


def _clean_scene(plan: dict) -> typing.List[str]:
    """
    Prepares the (copied) scene for a game engine. Each step is its own
    function, so steps are easy to add, remove or reorder.

    Args:
        plan: The publish plan made by PublishRig._make_plan.

    Returns:
        A description of each step which was run, for the manifest.
    """
    # -- Baking must come first: it records what the control rig does to the
    # -- joints, before the control rig is deleted
    steps = [
        _bake_and_remove_constraints(plan["fbx_roots"]),
        _delete_nodes(plan["nodes_to_delete"]),
        _import_references(),
        _remove_namespaces(),
        _delete_unknown_nodes(),
        _delete_empty_groups(plan["fbx_roots"]),
    ]

    for step in steps:
        log.info(f"Publish cleanup : {step}")

    return steps


def _bake_and_remove_constraints(roots: typing.List[str]) -> str:
    """
    Bakes the transforms of every joint under the roots to keys over the
    playback range, then deletes the constraints under the roots. The joints
    then move exactly as before, without needing the control rig.
    """
    joints = cmds.ls(roots, type="joint") + (
        cmds.listRelatives(roots, allDescendents=True, type="joint", fullPath=True) or []
    )

    if not joints:
        return "bake: no joints found under the FBX Roots"

    # -- Locked or non-keyable channels (such as those from the Lock And Hide
    # -- example) cannot be keyed, so open them up first. This is only the
    # -- copy of the scene, so nothing the user sees is changed.
    for joint in joints:
        for attribute_name in TRANSFORM_ATTRIBUTES:
            cmds.setAttr(f"{joint}.{attribute_name}", lock=False, keyable=True)

    start = cmds.playbackOptions(query=True, minTime=True)
    end = cmds.playbackOptions(query=True, maxTime=True)

    # -- simulation=True evaluates every frame in order, which is needed when
    # -- one joint's motion depends on another's
    cmds.bakeResults(
        joints,
        time=(start, end),
        attribute=TRANSFORM_ATTRIBUTES,
        simulation=True,
    )

    descendants = cmds.listRelatives(roots, allDescendents=True, fullPath=True) or []
    constraints = cmds.ls(descendants, type="constraint") or []
    if constraints:
        cmds.delete(constraints)

    return f"bake: baked {len(joints)} joint(s) over frames {start:g}-{end:g} and deleted {len(constraints)} constraint(s)"


def _delete_nodes(nodes: typing.List[str]) -> str:
    """
    Deletes the given nodes, skipping any which do not exist.
    """
    existing = [node for node in nodes if cmds.objExists(node)]
    if existing:
        cmds.delete(existing)

    return f"delete nodes: deleted {len(existing)} of {len(nodes)} node(s)"


def _import_references() -> str:
    """
    Imports every loaded reference into the scene, and removes unloaded
    ones. Referenced nodes cannot have their namespaces removed, so this has
    to happen before _remove_namespaces.
    """
    imported = 0
    removed = 0

    for reference_file in cmds.file(query=True, reference=True) or []:
        if cmds.referenceQuery(reference_file, isLoaded=True):
            cmds.file(reference_file, importReference=True)
            imported += 1

        else:
            cmds.file(reference_file, removeReference=True)
            removed += 1

    return f"references: imported {imported} and removed {removed} unloaded"


def _remove_namespaces() -> str:
    """
    Removes every namespace, moving the nodes in each one into the root
    namespace. Engines usually treat "char:hips" and "hips" as different
    joints, so the names must not depend on how the asset was loaded.
    """
    namespaces = cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []

    # -- Maya's own namespaces cannot (and must not) be removed
    namespaces = [namespace for namespace in namespaces if namespace not in ("UI", "shared")]

    # -- Remove the deepest first, so a parent is never removed before its children
    for namespace in sorted(namespaces, key=lambda name: name.count(":"), reverse=True):
        cmds.namespace(removeNamespace=namespace, mergeNamespaceWithRoot=True)

    return f"namespaces: removed {len(namespaces)}"


def _delete_unknown_nodes() -> str:
    """
    Deletes nodes from plugins which are not loaded. They cannot be exported,
    and can stop the FBX exporter.
    """
    unknown_nodes = cmds.ls(type=["unknown", "unknownDag", "unknownTransform"]) or []

    for node in unknown_nodes:
        if cmds.objExists(node):
            cmds.lockNode(node, lock=False)
            cmds.delete(node)

    return f"unknown nodes: deleted {len(unknown_nodes)}"


def _delete_empty_groups(roots: typing.List[str]) -> str:
    """
    Deletes groups under the roots which have no children, repeating until
    there are none left, as deleting one empty group can empty its parent.
    """
    deleted = 0

    while True:
        descendants = cmds.listRelatives(roots, allDescendents=True, fullPath=True) or []

        # -- exactType skips joints, which are transforms too but should
        # -- always be exported
        empty = [
            node
            for node in cmds.ls(descendants, exactType="transform", long=True)
            if not cmds.listRelatives(node, children=True)
        ]

        if not empty:
            break

        cmds.delete(empty)
        deleted += len(empty)

    return f"empty groups: deleted {deleted}"


def _export_fbx(path: str, roots: typing.List[str]) -> None:
    """
    Exports the roots, and everything beneath them, to an FBX file.

    Args:
        path: The .fbx file to write.
        roots: The nodes to export.
    """
    cmds.loadPlugin("fbxmaya", quiet=True)

    # -- The FBX exporter remembers settings between exports, including ones
    # -- the user chose by hand. Reset them and set each one we rely on, so
    # -- every publish is exported the same way on every machine.
    mel.eval("FBXResetExport")
    for setting in (
            "FBXExportSkins -v true",
            "FBXExportShapes -v true",
            "FBXExportIncludeChildren -v true",
            "FBXExportInputConnections -v false",
            "FBXExportConstraints -v false",
            "FBXExportCameras -v false",
            "FBXExportLights -v false",
            "FBXExportBakeComplexAnimation -v false",
    ):
        mel.eval(setting)

    # -- MEL needs forward slashes, as it treats a backslash as an escape
    fbx_path = path.replace("\\", "/")

    cmds.select(roots, replace=True)
    mel.eval(f'FBXExport -f "{fbx_path}" -s')
    cmds.select(clear=True)


def _write_manifest(plan: dict) -> None:
    """
    Writes publish.json, describing who published what, when, and how.

    Args:
        plan: The publish plan made by PublishRig._make_plan.
    """
    manifest = {
        "asset": plan["asset"],
        "version": plan["version"],
        "rig": plan["rig"],
        "published_by": plan["published_by"],
        "published_at": plan["published_at"],
        "maya_version": cmds.about(version=True),
        "aniseed_version": aniseed.__version__,
        "packages": {package.name: package.version for package in aniseed.packages.discover()},
        "source_scene": plan["original_scene"] or "(unsaved scene)",
        # -- Paths relative to the version folder, so the publish can be moved
        "files": [os.path.relpath(path, plan["folder"]) for path in plan["files"]],
        "pre_flight_issues": plan["pre_flight_issues"],
        "cleanup_steps": plan["cleanup_steps"],
    }

    with open(plan["manifest"], "w") as f:
        json.dump(manifest, f, indent=4)


def _existing_versions(asset_folder: str) -> typing.List[int]:
    """
    Returns the version numbers of the v### folders in the asset folder.
    """
    if not os.path.isdir(asset_folder):
        return []

    return [
        int(match.group(1))
        for match in (re.match(r"^v(\d{3,})$", name) for name in os.listdir(asset_folder))
        if match
    ]


def _open_in_file_browser(folder: str) -> None:
    """
    Opens the folder in the operating system's file browser.
    """
    if sys.platform == "win32":
        os.startfile(folder)

    elif sys.platform == "darwin":
        subprocess.Popen(["open", folder])

    else:
        subprocess.Popen(["xdg-open", folder])
