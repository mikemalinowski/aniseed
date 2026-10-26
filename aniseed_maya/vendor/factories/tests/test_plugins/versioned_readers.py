import json

from factories.examples.reader import ReaderPlugin


# ------------------------------------------------------------------------------
class JSONReader(ReaderPlugin):
    """
    This is a specific plugin implementaiton for the data reader which
    wrangles the expected data in a very specific way to test versioning.
    """
    version = 2

    # --------------------------------------------------------------------------
    @classmethod
    def contents(cls, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)

            data['foo'] = 'not bar'

        return data

    # --------------------------------------------------------------------------
    @classmethod
    def can_read(cls, filepath):
        if filepath.endswith('.json'):
            return True

        return False


# ------------------------------------------------------------------------------
class MethodVersionReader(ReaderPlugin):
    """
    This is a specific plugin implementaiton for the data reader which
    wrangles the expected data in a very specific way to test versioning.
    """

    @classmethod
    def version(cls):
        return 1

    # --------------------------------------------------------------------------
    @classmethod
    def contents(cls, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)

            data['foo'] = 'not bar'

        return data

    # --------------------------------------------------------------------------
    @classmethod
    def can_read(cls, filepath):
        if filepath.endswith('.json'):
            return True

        return False

