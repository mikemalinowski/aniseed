import functools

try:
    from maya import cmds

except ImportError:
    cmds = None

# --------------------------------------------------------------------------------------
def undoable(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with UndoChunk():
            return func(*args, **kwargs)
    return wrapper


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class UndoChunk:

    # ----------------------------------------------------------------------------------
    def __init__(self, label="undo section"):
        self._closed = False
        self._label = label

    # ----------------------------------------------------------------------------------
    def __enter__(self):
        if cmds:
            cmds.undoInfo(openChunk=True, chunkName=self._label)
        return self

    # ----------------------------------------------------------------------------------
    def __exit__(self, *exc_info):
        if cmds and not self._closed:
            cmds.undoInfo(closeChunk=True)

    # ----------------------------------------------------------------------------------
    def restore(self):
        if not cmds:
            return
        cmds.undoInfo(closeChunk=True)
        self._closed = True

        try:
            cmds.undo()

        # -- Nothing to undo is not an error for a restore
        except RuntimeError:
            pass
