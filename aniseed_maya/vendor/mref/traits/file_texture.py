import os
import re
import glob

import mref
from maya import cmds
from maya.api import OpenMaya as om


class FileTexture(mref.Trait):
    """
    Trait bound to any node with ``MFn.kFileTexture`` — Maya ``file``
    texture nodes. Exposes the texture path, colour space, UV tiling
    (UDIM) mode, resolution of the path (environment variables, project
    relative paths and tile tokens) to the files on disk, and the
    ``place2dTexture`` node driving the texture's UVs.
    """

    # -- Index -> label for the uvTilingMode enum
    tiling_modes = ["off", "zbrush", "mudbox", "udim", "explicit"]

    # -- Tile / frame tokens Maya supports in file texture names
    _token_regex = re.compile(r"<(UDIM|UVTILE|u|v|U|V|f)>|#+")

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kFileTexture)

    def file_path(self) -> str:
        """
        Returns the texture path exactly as stored on the node
        (``fileTextureName``), including any tokens such as ``<UDIM>``.
        """
        return cmds.getAttr(f"{self.item.full_name()}.fileTextureName") or ""

    def set_file_path(self, path: str) -> None:
        """
        Sets the texture path (``fileTextureName``). Tokens such as
        ``<UDIM>`` are kept as-is.
        """
        cmds.setAttr(f"{self.item.full_name()}.fileTextureName", path, type="string")

    def colour_space(self) -> str:
        """
        Returns the name of the input colour space of the texture
        """
        return cmds.getAttr(f"{self.item.full_name()}.colorSpace")

    def set_colour_space(self, name: str) -> None:
        """
        Sets the input colour space of the texture. File rules are
        disabled on the node (``ignoreColorSpaceFileRules``) so the
        explicit choice is not overridden when the path changes.
        """
        node = self.item.full_name()
        cmds.setAttr(f"{node}.ignoreColorSpaceFileRules", True)
        cmds.setAttr(f"{node}.colorSpace", name, type="string")

    def tiling_mode(self) -> str:
        """
        Returns the UV tiling mode as one of ``"off"``, ``"zbrush"``,
        ``"mudbox"``, ``"udim"`` or ``"explicit"``.
        """
        return self.tiling_modes[cmds.getAttr(f"{self.item.full_name()}.uvTilingMode")]

    def set_tiling_mode(self, mode: str) -> None:
        """
        Sets the UV tiling mode — one of ``"off"``, ``"zbrush"``,
        ``"mudbox"``, ``"udim"`` or ``"explicit"``.
        """
        if mode not in self.tiling_modes:
            raise ValueError(f"Unknown tiling mode {mode!r}; expected one of {self.tiling_modes}")
        cmds.setAttr(f"{self.item.full_name()}.uvTilingMode", self.tiling_modes.index(mode))

    def is_tiled(self) -> bool:
        """
        Returns True if the texture uses any UV tiling mode (UDIM etc)
        """
        return cmds.getAttr(f"{self.item.full_name()}.uvTilingMode") != 0

    def resolved_paths(self) -> list[str]:
        """
        Returns the absolute paths of the texture files on disk. Environment
        variables and project-relative paths are expanded. For tiled or
        sequence textures, tile/frame tokens (``<UDIM>``, ``<UVTILE>``,
        ``<u>``/``<v>``, ``<f>``, ``#``) are expanded against the files that
        exist on disk, returned sorted. For a plain path the single expanded
        path is returned whether or not it exists; an empty path returns
        an empty list.
        """
        path = self._expanded_path()
        if not path:
            return []

        if not self._token_regex.search(path):
            return [path]

        # -- glob.escape leaves the <...> tokens untouched, so escape any
        # -- glob characters in the real path first and then swap the
        # -- tokens for wildcards.
        pattern = self._token_regex.sub("*", glob.escape(path))

        return sorted(
            os.path.normpath(match).replace("\\", "/")
            for match in glob.glob(pattern)
        )

    def file_exists(self) -> bool:
        """
        Returns True if the texture file exists on disk. For tiled
        textures this is True if at least one tile exists.
        """
        return any(os.path.isfile(path) for path in self.resolved_paths())

    def place2d_texture(self) -> mref.ReferencedItem|None:
        """
        Returns the ``place2dTexture`` node driving this texture's UV
        coordinates, or None if it is not connected to one.
        """
        sources = cmds.listConnections(
            f"{self.item.full_name()}.uvCoord",
            source=True,
            destination=False,
        ) or []

        for source in sources:
            if cmds.nodeType(source) == "place2dTexture":
                return mref.get(source)

        return None

    def _expanded_path(self) -> str:
        path = self.file_path()
        if not path:
            return ""

        path = os.path.expandvars(os.path.expanduser(path))

        if not os.path.isabs(path):
            path = cmds.workspace(expandName=path)

        return os.path.normpath(path).replace("\\", "/")
