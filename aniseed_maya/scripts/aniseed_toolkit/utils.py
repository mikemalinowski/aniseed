try:
    import maya.cmds as mc

except:
    mc = None

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
    def __init__(self, label="undo section"):
        self._closed = False
        self._label = label

    # ----------------------------------------------------------------------------------
    def __enter__(self):
        if mc:
            mc.undoInfo(openChunk=True, chunkName=self._label)
        return self

    # ----------------------------------------------------------------------------------
    def __exit__(self, *exc_info):
        if mc and not self._closed:
            mc.undoInfo(closeChunk=True)

    # ----------------------------------------------------------------------------------
    def restore(self):
        if not mc:
            return
        mc.undoInfo(closeChunk=True)
        self._closed = True

        try:
            mc.undo()

        except StandardError:
            pass
