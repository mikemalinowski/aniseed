import os
import sys
import shutil
import PySide6
import traceback


# -- Run a check to ensure we're running within maya
try:
    import maya.cmds as mc
    within_maya = True

except ImportError:
    within_maya = False


# ------------------------------------------------------------------------------
def confirmation(title='Text Request', label='', parent=None, **kwargs):
    """
    Quick and easy access for getting text input. You do not have to have a
    QApplication instance, as this will look for one.

    :return: str, or None
    """
    answer = PySide6.QtWidgets.QMessageBox.warning(
        parent,
        title,
        label,
        PySide6.QtWidgets.QMessageBox.Yes,
        PySide6.QtWidgets.QMessageBox.No,
    )

    if answer == PySide6.QtWidgets.QMessageBox.Yes:
        return True

    return False


# ------------------------------------------------------------------------------
def message(title='Text Request', label='', parent=None, **kwargs):
    """
    Quick and easy access for getting text input. You do not have to have a
    QApplication instance, as this will look for one.

    :return: str, or None
    """
    PySide6.QtWidgets.QMessageBox.information(
        parent,
        title,
        label,
    )

    return True


# ------------------------------------------------------------------------------
def clear_folder(folder_path):

    if not os.path.exists(folder_path):
        return True

    success = True

    for filename in os.listdir(folder_path):

        if "aniseed" not in filename:
            continue

        filepath = os.path.join(
            folder_path,
            filename,
        )

        try:
            if os.path.isfile(filepath) or os.path.islink(filepath):
                os.unlink(filepath)

            elif os.path.isdir(filepath):
                shutil.rmtree(filepath)

        except Exception as err:
            print(f'Failed to remove {filepath}. Error Given: {err}')
            success = False

    return success


# ------------------------------------------------------------------------------
def install_aniseed():

    destination = os.path.join(
        os.environ["MAYA_APP_DIR"],
        "modules",
    )

    try:
        shutil.copytree(
            os.path.dirname(__file__),
            destination,
            dirs_exist_ok=True,
        )

    except:
        print(traceback.print_exc())
        return False

    # -- Load the module
    mc.loadModule(scan=True)
    # mc.loadModule(allModules=True)
    mc.loadModule(
        ld=os.path.join(
            destination,
            "aniseed.mod",
        ),
    )

    return True


# ------------------------------------------------------------------------------
def uninstall_aniseed():

    try:
        existing_location = mc.getModulePath(moduleName="Aniseed")

    except RuntimeError:
        existing_location = os.path.join(
            os.environ["MAYA_APP_DIR"],
            "modules",
            "aniseed_maya"
        )

    if not os.path.exists(existing_location):
        print("No existing version of aniseed found")
        return True

    # -- To reach here we have an existing version of aniseed, so we need
    # -- to uninstall that first. But before we do, lets ask.
    user_confirmation = confirmation(
        title="Existing Aniseed Found",
        label=(
            "An existing version of aniseed has been found. \n\n"
            "This installer will remove it before installing\n" 
            "the new version.\n"
            "Are you sure you want to continue?"
        )
    )

    if not user_confirmation:
        print("User cancelled uninstall")
        return False

    return clear_folder(
        os.path.dirname(existing_location),
    )


# ------------------------------------------------------------------------------
def tear_down():

    if "drag_drop_install" in sys.modules:
        print("removing installer from modcule cache")
        del sys.modules["drag_drop_install"]


# ------------------------------------------------------------------------------
def onMayaDroppedPythonFile(*args, **kwargs):
    """
    This function is only supported since Maya 2017 Update 3.
    Maya requires this in order to successfully execute.
    """
    pass



# ------------------------------------------------------------------------------
if within_maya:
    if uninstall_aniseed():
        if install_aniseed():
            message(
                title="Aniseed Install Complete",
                label=(
                    "Aniseed has been successfully installed.\n\n"
                    "Please restart Maya"
                )
            )

        else:
            message(
                title="Aniseed Install Error",
                label=(
                    "Aniseed failed to install correctly. \n\n"
                    "Please check the script editor for details"
                )
            )

    tear_down()
