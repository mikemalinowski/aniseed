import maya.cmds as mc


# --------------------------------------------------------------------------------------
def undoable(func):
    def wrapper(*args, **kwargs):
        with UndoChunk():
            return func(*args, **kwargs)
    return wrapper


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class UndoChunk(object):

    # ----------------------------------------------------------------------------------
    def __init__(self):
        self._closed = False

    # ----------------------------------------------------------------------------------
    def __enter__(self):
        mc.undoInfo(openChunk=True)
        return self

    # ----------------------------------------------------------------------------------
    def __exit__(self, *exc_info):
        if not self._closed:
            mc.undoInfo(closeChunk=True)

    # ----------------------------------------------------------------------------------
    def restore(self):
        mc.undoInfo(closeChunk=True)
        self._closed = True

        try:
            mc.undo()

        except StandardError:
            pass
