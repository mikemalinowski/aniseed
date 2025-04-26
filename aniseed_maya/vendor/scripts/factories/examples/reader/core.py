import os
import factories


# ------------------------------------------------------------------------------
class DataReader(object):
    """
    This class represents a generic fruit reader capable of parsing
    fruit data in multiple formats seamlessly
    """

    # --------------------------------------------------------------------------
    def __init__(self):
        self.factory = factories.Factory(
            abstract=ReaderPlugin,
            versioning_identifier='version',
            paths=[
                os.path.join(
                    os.path.dirname(__file__),
                    'readers',
                )
            ]
        )

    # --------------------------------------------------------------------------
    def read(self, filepath):
        """
        Generic read method which will cycle over all the available plugins
        and utilise the one which is capable of operating on the given file

        :param filepath: Absolute path to data to be read
        :type filepath: str

        :return: Dictionary of data stored in the file
        :rtype: dict
        """
        for plugin in self.factory.plugins():

            if plugin.can_read(filepath):
                return plugin.contents(filepath)

        raise Exception(
            'No plugin able to read : %s' % filepath
        )


# ------------------------------------------------------------------------------
class ReaderPlugin(object):

    version = 1

    def contents(self, filepath):
        """
        This should return a dictionary of data collated from the
        file.

        Note: This MUST be re-implemented in the plugin

        :param filepath: Absolute filepath to file
        :type filepath: str

        :return: dictionary of data taken from the file
        :rtype: dict
        """
        return dict()

    @classmethod
    def can_read(cls, filepath):
        """
        Checks whether this plugin is capable of operating
        on the given file

        :param filepath: Absolute path to the file to test
        :type filepath: str

        :return: True if the plugin can operate on the file
        :rtype: bool
        """
        return False
