from factories.examples.reader import ReaderPlugin


# ------------------------------------------------------------------------------
class BlankReader(ReaderPlugin):
    """
    This reader has no direct functionality and is here only to serve as 
    a test case for the factory unittests
    """
    version = 1

    # --------------------------------------------------------------------------
    @classmethod
    def contents(cls, filepath):
        return dict()

    # --------------------------------------------------------------------------
    @classmethod
    def can_read(cls, filepath):
        return False

