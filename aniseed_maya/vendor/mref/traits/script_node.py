import mref
from maya import cmds
from maya.api import OpenMaya as om


# -- The values of the script node's scriptType attribute, in index order
SCRIPT_TYPES = (
    "demand",
    "open_close",
    "gui_open_close",
    "ui_configuration",
    "software_render",
    "software_frame_render",
    "scene_configuration",
    "time_changed",
)

# -- The values of the script node's sourceType attribute, in index order
SOURCE_TYPES = (
    "mel",
    "python",
)


class ScriptNode(mref.Trait):
    """
    Trait bound to any node with ``MFn.kScript`` — script nodes created
    by ``cmds.scriptNode``. Exposes the before / after scripts, when the
    scripts run (the script type), which language they are written in
    (the source type), and lets them be executed on demand.

    Script types are reported as one of the names in ``SCRIPT_TYPES``
    (``"demand"``, ``"open_close"``, ``"gui_open_close"``,
    ``"ui_configuration"``, ``"software_render"``,
    ``"software_frame_render"``, ``"scene_configuration"``,
    ``"time_changed"``) and source types as ``"mel"`` or ``"python"``.
    Setters accept either the name or Maya's integer index.
    """

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kScript)

    def before_script(self) -> str:
        """
        Returns the "before" script — run on scene open, render start or
        time change depending on the script type, or by
        :meth:`execute_before`.
        """
        return cmds.scriptNode(self.item.full_name(), query=True, beforeScript=True) or ""

    def set_before_script(self, script: str) -> None:
        """
        Sets the "before" script
        """
        cmds.scriptNode(self.item.full_name(), edit=True, beforeScript=script)

    def after_script(self) -> str:
        """
        Returns the "after" script — run on scene close or render end
        depending on the script type, or by :meth:`execute_after`.
        """
        return cmds.scriptNode(self.item.full_name(), query=True, afterScript=True) or ""

    def set_after_script(self, script: str) -> None:
        """
        Sets the "after" script
        """
        cmds.scriptNode(self.item.full_name(), edit=True, afterScript=script)

    def script_type(self) -> str:
        """
        Returns when this script node's scripts are run, as one of the
        names in ``SCRIPT_TYPES``.
        """
        return SCRIPT_TYPES[cmds.scriptNode(self.item.full_name(), query=True, scriptType=True)]

    def set_script_type(self, script_type: str|int) -> None:
        """
        Sets when this script node's scripts are run. Accepts a name from
        ``SCRIPT_TYPES`` or Maya's integer index.
        """
        cmds.scriptNode(
            self.item.full_name(),
            edit=True,
            scriptType=_index(script_type, SCRIPT_TYPES),
        )

    def source_type(self) -> str:
        """
        Returns the language the scripts are written in, ``"mel"`` or
        ``"python"``.
        """
        return SOURCE_TYPES[cmds.getAttr(f"{self.item.full_name()}.sourceType")]

    def set_source_type(self, source_type: str|int) -> None:
        """
        Sets the language the scripts are written in. Accepts ``"mel"``,
        ``"python"`` or Maya's integer index.
        """
        cmds.scriptNode(
            self.item.full_name(),
            edit=True,
            sourceType=SOURCE_TYPES[_index(source_type, SOURCE_TYPES)],
        )

    def execute_before(self) -> None:
        """
        Runs the "before" script now
        """
        cmds.scriptNode(self.item.full_name(), executeBefore=True)

    def execute_after(self) -> None:
        """
        Runs the "after" script now
        """
        cmds.scriptNode(self.item.full_name(), executeAfter=True)


def _index(value: str|int, names: tuple) -> int:
    """
    Resolves a name or integer index into an index into ``names``,
    raising ValueError if it is not valid.
    """
    if isinstance(value, str):
        if value not in names:
            raise ValueError(f"{value!r} is not one of {names}")
        return names.index(value)

    if not 0 <= value < len(names):
        raise ValueError(f"{value!r} is not a valid index for {names}")
    return value
