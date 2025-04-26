import os
import inspect
import factories

from . import utils

class Tool:
    """
    Documentation to go here.
    """

    # -- This is the label that is used to
    # -- retrieve and display the tool
    identifier = ""

    # -- This should be left as one unless you want
    # -- to specifically deprecate your tool by adding
    # -- a new version of it
    version = 1

    # -- Categories are like folders and are a good way
    # -- to organise tools. Your tool will show in any
    # -- categories you define here
    categories = []

    # -- A tool may be given an icon
    icon = ""

    # -- The classification is a way of collating all tools into
    # -- larger groups. For instance, Rigging or Animation. That way
    # -- the user can invoke the toolkit tool and only see tools of
    # -- a particular classification
    classification = ""

    # -- Some tools can be code only. If this is the case
    # -- then set this to False and it will not be visible
    # -- through the ui, but is accessible through code.
    user_facing = True

    def run(self, *args, **kwargs):
        pass

    def ui_elements(self, keyword_name):
        """
        This allows you to optionally return a QWidget to represent
        the given keyword argument in a ui if you wish to. If not then
        a widget will attempted to be auto resolved based on the type.

        Note, if you use a custom widget then you must implement a
        get_value() and set_value() method, as well as a changed signal.
        """
        return None

    def test(self):
        """
        This should be used to test the functionality of the tool and
        return True if it is working as expected
        """
        return True


class ToolBox(factories.Factory):
    """
    This is a factory that contains all the tool's. It typically
    should be used as a singleton to prevent tools from continously
    being reloaded.
    """

    # -- Store the sharable instance
    _INSTANCE = None

    def __init__(self):
        super(ToolBox, self).__init__(
            plugin_identifier="identifier",
            versioning_identifier="version",
            abstract=Tool,
            paths=[
                os.path.join(
                    os.path.dirname(__file__),
                    "tools",
                ),
            ],
        )

    def run(self, tool_name, *args, **kwargs):

        if tool_name not in self.identifiers():
            raise Exception(f"{tool_name} is not a valid tool name.")

        with utils.UndoChunk():
            return self.instance(tool_name).run(*args, **kwargs)

    def categories(self) -> list[str]:
        """
        This will return all the categories defined by the tools
        in the toolbox
        """
        results = []

        for tool in self.plugins():
            results.extend(tool.categories)

        return list(set(results))

    def classifications(self) -> list[str]:
        results = []

        for tool in self.plugins():
            if tool.classification and tool.user_facing:
                results.append(tool.classification)

        return list(set(results))

    def signature(self, tool_identifier):
        """
        This will return a dictionary where the key is the parameter
        name and the value is the default value
        """
        result = dict()

        tool = self.instance(tool_identifier)
        signature = inspect.signature(tool.run)

        for name, param in signature.parameters.items():
            result[name] = param.default
        return result

    def documentation(self, tool_identifier):
        tool = self.request(tool_identifier)
        return (tool.__doc__ or "").strip()

    @classmethod
    def singleton(cls):
        """
        Calling this will return the shared instance of the toolbox
        """
        if cls._INSTANCE is None:
            cls._INSTANCE = ToolBox()

        return cls._INSTANCE


def run(tool_name, *args, **kwargs):
    return ToolBox.singleton().run(tool_name, *args, **kwargs)
