"""
The tool registry. Tools are user facing actions which the toolkit app (and
``aniseed_toolkit.run``) can find by identifier.

There are two ways to declare a tool:

1. Decorate a function with ``@tool(...)``. The function stays a normal
   function which can be called directly; the decorator only records it so the
   ToolBox can offer it as a tool.

    @tool("Get Joints Between", classification="Rigging", categories=["Joints"])
    def get_between(start: str = "", end: str = "") -> list[str]:
        ...

2. Subclass ``Tool`` (the original mechanism, still used for tools which need
   class level customisation such as bespoke ui_elements, and by any external
   plugins found through the ANISEED_TOOLKIT_PATHS environment variable).
"""
import os
import inspect
import functools

import factories

from . import utils


class Tool:
    """
    Base class for class based tools. The ToolBox finds subclasses of this in
    the tools directories (and any ANISEED_TOOLKIT_PATHS locations).
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
        """
        Performs the tool's action. Subclasses implement this, and the
        arguments they declare are what the toolkit ui exposes.
        """
        pass

    @classmethod
    def ui_elements(cls, keyword_name):
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


# -- Functions declared as tools, keyed by (identifier, version). Re-executing
# -- a module (e.g. a reload) simply replaces the entry.
_FUNCTION_TOOLS = dict()


def tool(
        identifier: str,
        classification: str = "",
        categories: list[str] = None,
        user_facing: bool = True,
        version: int = 1,
        icon: str = "",
):
    """
    Declares the decorated function as a tool. The function itself is returned
    unchanged, so it remains a normal function for code to call.

    Args:
        identifier: The name the tool is found (and run) by
        classification: The broad group of the tool, e.g. "Rigging"
        categories: The categories (folders) the tool shows in
        user_facing: If False the tool is only available through code
        version: The version of the tool
        icon: An optional icon path for the tool

    Returns:
        The decorator
    """
    def decorator(func):
        func.tool_info = dict(
            identifier=identifier,
            classification=classification,
            categories=list(categories or []),
            user_facing=user_facing,
            version=version,
            icon=icon,
        )
        _FUNCTION_TOOLS[(identifier, version)] = func

        # -- If the toolbox already exists (the module defining the tool was
        # -- imported late) register the tool straight away
        if ToolBox._INSTANCE is not None:
            ToolBox._INSTANCE.register(tool_class_from_function(func))

        return func

    return decorator


def tool_class_from_function(func) -> type:
    """
    Wraps a function declared with @tool in a Tool subclass so that the
    factory (and the toolkit ui) can treat it like any other tool. The
    class's run() has the function's signature and documentation.

    Args:
        func: The function decorated with @tool

    Returns:
        A Tool subclass
    """
    info = func.tool_info

    @functools.wraps(func)
    def run(self, *args, **kwargs):
        return func(*args, **kwargs)

    # -- Expose the function's signature (with self) so the ui can build
    # -- its form from the parameters
    signature = inspect.signature(func)
    run.__signature__ = signature.replace(
        parameters=[inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        + list(signature.parameters.values()),
    )

    return type(
        f"{func.__name__}_tool",
        (Tool,),
        dict(
            identifier=info["identifier"],
            classification=info["classification"],
            categories=info["categories"],
            user_facing=info["user_facing"],
            version=info["version"],
            icon=info["icon"],
            run=run,
            function=staticmethod(func),
            __doc__=func.__doc__,
            __module__=func.__module__,
        ),
    )


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
            envvar="ANISEED_TOOLKIT_PATHS",
        )
        self._register_function_tools()

    def _register_function_tools(self):
        """
        Registers every function declared with @tool
        """
        for func in _FUNCTION_TOOLS.values():
            self.register(tool_class_from_function(func))

    def reload(self):
        """
        Re-searches the tool paths. Function tools are registered again as
        the factory forgets them during the reload.
        """
        super(ToolBox, self).reload()
        self._register_function_tools()

    def run(self, tool_name, *args, **kwargs):
        """
        Runs the tool with the given identifier inside a single undo chunk,
        passing the given arguments to it, and returns the result.
        """
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

        for tool_ in self.plugins():
            results.extend(tool_.categories)

        return list(set(results))

    def classifications(self) -> list[str]:
        """
        Returns the classifications used by user facing tools
        """
        results = []

        for tool_ in self.plugins():
            if tool_.classification and tool_.user_facing:
                results.append(tool_.classification)

        return list(set(results))

    def signature(self, tool_identifier):
        """
        This will return a dictionary where the key is the parameter
        name and the value is the default value
        """
        result = dict()

        tool_ = self.instance(tool_identifier)
        signature = inspect.signature(tool_.run)

        for name, param in signature.parameters.items():
            result[name] = param.default
        return result

    def documentation(self, tool_identifier):
        """
        Returns the documentation string for the given tool
        """
        tool_ = self.request(tool_identifier)
        return (tool_.__doc__ or "").strip()

    @classmethod
    def singleton(cls):
        """
        Calling this will return the shared instance of the toolbox
        """
        if cls._INSTANCE is None:
            cls._INSTANCE = ToolBox()

        return cls._INSTANCE


def run(tool_name, *args, **kwargs):
    """
    Runs the tool with the given identifier (see ToolBox.run)
    """
    return ToolBox.singleton().run(tool_name, *args, **kwargs)


def register(tool_class):
    """
    This allows for a python module to register a tool without it being on the search
    path.
    """
    return ToolBox.singleton().register(tool_class)
