"""
This module is specifically intended for use when in environments where
you're actively trying to share/develop tools across multiple applications
which support PyQt, PySide or PySide2. 

The premise is that you can request the main application window using 
a common function regardless of the actual application - making it trivial
to implement a tool which works in multiple host applications without any
bespoke code.

The current list of supported applications are:

    * Native Python
    * Maya
    * 3dsmax
    * Motion Builder
    * Houdini

"""
import os
import sys
import scribble

from PySide6 import QtWidgets, QtCore


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming
def application() -> QtWidgets.QWidget:
    """
    Returns the main application window for the current environment
    
    Returns:
        Main window as a QWidget
    """
    for test_string, func_ in HOST_MAPPING.items():
        if test_string in sys.executable:
            return func_()


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
def _python():
    for candidate in QtWidgets.QApplication.topLevelWidgets():
        if isinstance(candidate, QtWidgets.QMainWindow):
            return candidate


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
def _findWindowByTitle(title):
    # -- Find the main application window
    for candidate in QtWidgets.QApplication.topLevelWidgets():
        # noinspection PyBroadException
        try:
            if title in candidate.windowTitle():
                return candidate
        except: pass


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming
def _3dsmax():
    return _findWindowByTitle('Autodesk 3ds Max')


# ------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
def _maya():
    from maya import OpenMayaUI as omui
    from shiboken6 import wrapInstance
    return wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming
def _houdini():
    import hou
    return hou.qt.mainWindow()


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming
def _mobu():
    return _findWindowByTitle('MotionBuilder 20')


# -- We support out the box native python but also a series
# -- of applications which run python embedded within them.
HOST_MAPPING = {
    "maya.exe": _maya,
    "mayapy.exe": _maya,
    "motionbuilder.exe": _mobu,
    "3dsmax.exe": _3dsmax,
    "houdini.exe": _houdini,
    "houdinifx.exe": _houdini,
    "houdinicore.exe": _houdini,
    "python.exe": _python,
    "pythonw.exe": _python,
}


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming,PyUnresolvedReferences
class MemorableWindow(QtWidgets.QMainWindow):
    """
    This Window has a built-in mechanism to automatically store and restore
    its geometry.
    """
    # -- How many pixels of a window we expect to see
    # -- before we re-position it
    _SCREEN_BUFFER = 12

    # _STORE_DIR = os.environ['APPDATA']

    # --------------------------------------------------------------------------
    def __init__(self, storage_identifier=None, offsetX=7, offsetY=32, *args, **kwargs):
        super(MemorableWindow, self).__init__(*args, **kwargs)

        self._offsetX = offsetX
        self._offsetY = offsetY
        self._storage_identifier = storage_identifier
        print("stor : %s "% self._storage_identifier)

        # -- If we're given an id, set this object name
        if self._storage_identifier:
            self.setObjectName(self._storage_identifier)

            # -- If there is any scribble data for this id we should
            # -- update this windows geometry accordingly.
            self.restoreSize()

    # --------------------------------------------------------------------------
    def save(self):
        settings = QtCore.QSettings('quteSettings', self.objectName())
        settings.setValue('windowState', self.saveState())
        self.storeSize()

    # --------------------------------------------------------------------------
    def closeEvent(self, event):
        self.save()
        super(MemorableWindow, self).closeEvent(event)

    # --------------------------------------------------------------------------
    def restoreSize(self):
        print("ID : %s" % self._storage_identifier)
        try:
            stored_data = scribble.get(self._storage_identifier)
            print("got data from : %s" % self._storage_identifier)
        except:
            stored_data = dict()

        # -- Get the screen rect, as we need to make sure
        # -- we're not about to open the window offscreen
        screen_rect = QtWidgets.QApplication.primaryScreen().geometry()

        if 'geometry' not in stored_data:
            return

        geom = stored_data['geometry']

        # -- Ensure the window is not too far off to the left
        # -- side of the screen, and ensure that we see at least
        # -- some of the window
        if geom[0] + (geom[2] - self._SCREEN_BUFFER) < 0:
            geom[0] = 300

        # -- Ensure that its not too far to the right, making
        # -- sure that we see at least some of the window
        if geom[0] + self._SCREEN_BUFFER > screen_rect.width():
            geom[0] = 300

        # -- Check if the window is above the available monitor space
        # -- we dont need to use the buffer on this, because we dont
        # -- want the title bar to go too high
        if geom[1] < 0:
            geom[1] = 300

        # -- Check if the window is below the monitor with at least
        # -- a small amount of the title bar to grab
        if geom[1] + self._SCREEN_BUFFER > screen_rect.height():
            geom[1] = 300

        self.setGeometry(
            geom[0],
            geom[1],
            geom[2],
            geom[3],
        )

    # --------------------------------------------------------------------------
    def storeSize(self):

        stored_data = scribble.get(self._storage_identifier)
        stored_data['geometry'] = [
            self.pos().x() + self._offsetX,
            self.pos().y() + self._offsetY,
            self.width(),
            self.height(),
        ]
        stored_data.save()
        print("saved data to : %s" % self._storage_identifier)

    # --------------------------------------------------------------------------
    def resizeEvent(self, event):
        self.storeSize()
        super(MemorableWindow, self).resizeEvent(event)

    # --------------------------------------------------------------------------
    def moveEvent(self, event):
        self.storeSize()
        super(MemorableWindow, self).moveEvent(event)

    # --------------------------------------------------------------------------
    def hideEvent(self, event):
        self.storeSize()
        super(MemorableWindow, self).hideEvent(event)
