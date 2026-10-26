import traceback
from maya import cmds


def suspended_viewport(func):
    def _inner(*args, **kwargs):
        cmds.refresh(suspend=True)
        failed = False
        result = None
        try:
            result = func(*args, **kwargs)
        except:
            traceback.print_exc()
            failed = True
        finally:
            cmds.refresh(suspend=False)

        if failed:
            raise Exception("Exception Encountered")

        return result
    return _inner


def undoable(func):
    def _inner(*args, **kwargs):
        cmds.undoInfo(openChunk=True, chunkName=func.__name__)
        failed = False
        result = None
        try:
            result = func(*args, **kwargs)
        except:
            traceback.print_exc()
            failed = True
        finally:
            cmds.undoInfo(closeChunk=True)

        if failed:
            raise Exception("Exception Encountered")

        return result
    return _inner


def retained_selection(func):
    def _inner(*args, **kwargs):
        selection = cmds.ls(selection=True)
        failed = False
        result = None
        try:
            result = func(*args, **kwargs)
        except:
            traceback.print_exc()
            failed = True
        finally:
            cmds.select(selection)

        if failed:
            raise Exception("Exception Encountered")

        return result
    return _inner