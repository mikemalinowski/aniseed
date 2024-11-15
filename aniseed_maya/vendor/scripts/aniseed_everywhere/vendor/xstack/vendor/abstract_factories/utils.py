import inspect
import os
import re
import sys
import types
import uuid

from .constants import LOGGER


try:
    basestring
except NameError:
    basestring = str


PYTHON_FILENAME_PATTERN = re.compile(
    r'[^_ \d]?[\w]*?'   # Doesn't start with number, space or underscore
    r'\.py[c]?$'        # Ends with .py, .pyc
)


# ------------------------------------------------------------------------------
# Generate a python version compatible import from file function
if sys.version_info >= (3, 5):
    import importlib.util

    def _import_from_filepath(module_name, filepath):
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

elif sys.version_info >= (3, 0):
    from importlib.machinery import SourceFileLoader
    import importlib.util

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

# -- Python 2.7
else:
    # noinspection PyUnresolvedReferences
    import imp

    def _import_from_filepath(module_name, filepath):
        ext = os.path.splitext(filepath)[1]
        if ext == '.py':
            module = imp.load_source(module_name, filepath)
        elif ext == '.pyc':
            with open(filepath, 'rb') as fp:
                module = imp.load_compiled(module_name, filepath, fp)
        else:
            raise ImportError('File type "{}" not supported (.py or .pyc only).'.format(ext))
        return module


# ------------------------------------------------------------------------------
def is_module(obj):
    """
    Get if <obj> is a module.
    :param object obj: Object to check.
    :rtype: bool
    """
    return isinstance(obj, types.ModuleType)


def ensure_iterable(objects):
    """
    Convenience function to ensure <objects> is iterable, returning a list if not.
    If objects is string type, [objects] is returned.
    :param any objects: Objects to affect.
    :rtype: list, tuple, set, frozenset, types.GeneratorType
    """
    if not objects:
        return []

    if isinstance(objects, (list, tuple, set, frozenset, types.GeneratorType)):
        return objects
    elif isinstance(objects, basestring):
        return [objects]

    return list(objects)


def generate_unique_name_from_filepath(filepath):
    """
    Generate a unique name from <filepath>.
    :param str filepath: Filepath to use.
    :rtype: str
    """
    filename = os.path.splitext(os.path.basename(filepath))[0]
    return '{}_{}'.format(filename, uuid.uuid4().hex)


def import_from_filepath(filepath, module_name=None):
    """
    Import <filepath> as a ModuleType called <module_name> (auto-generated if None given).
    :param str filepath: Filepath to import as module.
    :param Optional[str] module_name: Module name to import as.
    :rtype: ModuleType
    """
    module_name = module_name or generate_unique_name_from_filepath(filepath)
    module = None
    try:
        LOGGER.debug('Loading "{}" into modulename "{}".'.format(filepath, module_name))
        module = _import_from_filepath(module_name, filepath)
        if not module:
            raise TypeError('Only .py and .pyc files are supported. Received "{}".'.format(filepath))
    except Exception as e:
        LOGGER.exception('Failed to load from "{}" :: {}.'.format(filepath, e))
    return module


def get_source_filepath(obj):
    """
    Get the source filepath of <obj>.
    :param object|type|ModuleType obj: Object to check.
    :rtype: str
    """
    if not inspect.ismodule(obj):
        return inspect.getfile(obj)
    elif not inspect.isclass(obj):
        obj = obj.__class__

    try:
        source_filepath = inspect.getsourcefile(obj)
    except TypeError:
        source_filepath = ''
    return source_filepath


def normalise_path(path):
    """
    Expand and normalise <path> to its real path.
    os.sep is replaced with os.altsep (where applicable).
    :param str path: Path to normalise.
    :rtype: str
    """
    norm_path = os.path.normcase(os.path.normpath(os.path.realpath(path)))
    if os.altsep:
        norm_path = norm_path.replace(os.sep, os.altsep)
    return norm_path


def iter_python_files(path, recursive=True):
    """
    Iterate the python files found from <path>.
    If <path> is a python file, yield that.
    If <path> is a directory, iterate nested python files.
    :param str path: Path to find python files from.
    :param bool recursive: True to iterate recursively.
    :rtype: Generator[str]
    """
    # TODO: Handle .zip python packages.
    if os.path.isfile(path):
        if PYTHON_FILENAME_PATTERN.match(os.path.basename(path)):
            yield normalise_path(path)
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for filename in files:
                if not PYTHON_FILENAME_PATTERN.match(filename):
                    continue

                yield normalise_path(os.path.join(root, filename))

            if not recursive:
                break
    else:
        LOGGER.error('iter_python_files >> {} is not an existing file or directory.'.format(path))
        return
