import os

from importlib.machinery import SourceFileLoader
import importlib.util


APPS_LOCATION = os.path.join(
    os.path.dirname(__file__),
    "apps",
)

FALLBACK_APP = "standalone"


def get_registration_file(app_name):
    return os.path.join(
        APPS_LOCATION,
        app_name,
        "register.py",
    )

def resident_apps():
    """
    Returns a list of the app implementations available

    :return:
    """
    results = list()

    for app_dir in os.listdir(APPS_LOCATION):

        registration_file = get_registration_file(app_dir)

        if os.path.exists(registration_file):

            if app_dir == FALLBACK_APP:
                results.append(
                    app_dir
                )

            else:
                results.insert(
                    0,
                    app_dir
                )

    return results


def get_usable_app():

    for app_dir in resident_apps():
        print("testing : %s" % app_dir)
        registration_file = get_registration_file(app_dir)

        if not os.path.exists(registration_file):
            print("no reg file")
            continue

        try:
            module_name = f"crosswalk_{app_dir}_registrar"
            module_ = _import_from_filepath(f"crosswalk_{app_dir}_registrar", registration_file)

            if not module_:
                continue

            module_name = f"crosswalk_{app_dir}"
            module_ = _import_from_filepath(f"crosswalk_{app_dir}", registration_file.replace("register.py", "__init__.py"))

            if module_:
                print("got module : %s" % module_name)
                return module_name

        except ImportError:
            continue


def _import_from_filepath(module_name, filepath):
    ext = os.path.splitext(filepath)[1]
    if ext == '.py':
        module = SourceFileLoader(module_name, filepath).load_module()
    elif ext == '.pyc':
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        raise ImportError('File type "{}" not supported (.py or .pyc only).'.format(ext))
    return module
