"""
The framework aniseed's toolkits (such as the Rigging and Animation toolkits)
are built on. A toolkit is a window of tools, each of which is an xstack
component (see core.Tool) with options only. Running a tool builds just that
component, as one undo step.

A toolkit is an aniseed package with:

    * a "toolkit" entry in its aniseed_package.json, naming the toolkit
    * a launch() function in its __init__, which calls
      aniseed.host.get().launch_toolkit(<its ToolkitConfig>)
    * its tools in its tools folder

Any active package can add tools to any toolkit, from its own tools folder.

    from aniseed import toolkits

    toolkits.launch("Rigging")
    toolkits.run("Zero Selection", options={"Key On Reset": True})

This package has no application code. Hosts give tools their context (such
as an undo chunk) through EmbeddedHost.tool_context, and show the windows
through EmbeddedHost.launch_toolkit. The window itself is in the app module,
which is only imported when a window is shown.
"""
import typing
import logging
import importlib

from .core import Tool
from .core import Organiser
from .core import ToolkitStack
from .core import clipboard
from .core import GENERAL
from .core import FAVOURITES

from . import core

from .. import packages as _packages

log = logging.getLogger(__name__)

# -- The toolkit names already warned about as being declared by more than one
# -- package, so the warning is only given once per session
_WARNED_DUPLICATES = set()


# --------------------------------------------------------------------------------------
def packages() -> typing.List[_packages.AniseedPackage]:
    """
    Returns the active aniseed packages which are toolkits (their
    aniseed_package.json has a "toolkit" entry), sorted by toolkit name.

    Only one package may declare a given toolkit. If more than one does, a
    warning is logged and only the first (in discovery order) is returned
    (launch still tries each of them, until one has a launch function).
    """
    declared = dict()

    for package in _packages.active():
        toolkit = package.metadata.get("toolkit")
        if not toolkit:
            continue

        if toolkit in declared:
            if toolkit not in _WARNED_DUPLICATES:
                _WARNED_DUPLICATES.add(toolkit)
                log.warning(
                    f"Aniseed packages {declared[toolkit].name} and {package.name} both declare "
                    f"the {toolkit!r} toolkit. Only the "
                    f"package which provides the toolkit window should have a \"toolkit\" entry in "
                    f"its aniseed_package.json - tools choose their toolkit with their toolkit attribute."
                )
            continue

        declared[toolkit] = package

    return sorted(declared.values(), key=lambda package: package.metadata["toolkit"])


# --------------------------------------------------------------------------------------
def names() -> typing.List[str]:
    """
    Returns the names of the active toolkits, such as ["Animation", "Rigging"].
    """
    return [package.metadata["toolkit"] for package in packages()]


# --------------------------------------------------------------------------------------
def launch(toolkit: str):
    """
    Opens the window of the named toolkit, through the active aniseed package
    which declares it.

    Args:
        toolkit: The name of the toolkit, such as "Rigging".

    Returns:
        The toolkit's window.

    Raises:
        ValueError: If no active package declares the toolkit (with a
            launch function).
    """
    # -- Gathered through packages() so any duplicate declarations are warned
    # -- about, but every declaring package is tried, in discovery order, as
    # -- the first may not be the one which provides the window
    names_ = names()

    for package in _packages.active():
        if package.metadata.get("toolkit") != toolkit:
            continue

        module = importlib.import_module(package.name)
        if callable(getattr(module, "launch", None)):
            return module.launch()

        log.warning(f"Aniseed package {package.name} declares the {toolkit!r} toolkit, but has no launch() function")

    raise ValueError(f"There is no active toolkit called {toolkit!r} with a launch() function. Active toolkits: {names_}")


# --------------------------------------------------------------------------------------
def run(identifier: str, options: typing.Optional[typing.Dict] = None) -> bool:
    """
    Runs a toolkit tool without its window, as the window would: checking it
    with is_valid, then running it within the host's tool_context (one undo
    step). This suits shelf buttons, hotkeys, scripts and tests.

    Options which are not given keep their default values, not the values the
    user last set in the toolkit's window.

    Tools are actions, so nothing is returned from them. Code which needs a
    value should call the library the tool uses instead.

        toolkits.run("Zero Selection", options={"Key On Reset": True})

    Args:
        identifier: The identifier of the tool, such as "Zero Selection".
        options: The values to give the tool's options, by option name.

    Returns:
        True if the tool ran successfully, False if it could not run
        (is_valid failed) or failed.

    Raises:
        ValueError: If there is no such tool, or it has no option with one
            of the given names.
    """
    stack = core.ToolkitStack("")
    tool_class = stack.component_library.request(identifier)

    if tool_class is None or tool_class is core.Organiser:
        raise ValueError(f"There is no toolkit tool called {identifier!r}")

    stack.toolkit = tool_class.toolkit
    stack.label = tool_class.toolkit

    tool = stack.add_component(identifier, identifier)
    if tool is None:
        raise ValueError(f"The toolkit tool {identifier!r} could not be created (see the log)")

    for name, value in (options or dict()).items():
        option = tool.option(name)

        if option is None:
            raise ValueError(
                f"{identifier} has no option called {name!r}. "
                f"Its options are: {[option.name() for option in tool.options()]}"
            )

        option.set(value)

    return stack.build(build_only=tool)


# --------------------------------------------------------------------------------------
def document(toolkit: str, filepath: str = "") -> str:
    """
    Writes a markdown page describing a toolkit's tools: their categories,
    what each one does (its docstring) and its options.

    Args:
        toolkit: The name of the toolkit, such as "Rigging".
        filepath: Where to write the page. If not given, it is only returned.

    Returns:
        The markdown.
    """
    stack = core.ToolkitStack(toolkit)
    tools = stack.tools()
    categories = sorted({category for tool in tools for category in (tool.categories or [core.GENERAL])})

    lines = [f"# {toolkit} Toolkit", ""]

    for category in categories:
        lines.append(f"- [{category}](#{category.lower().replace(' ', '-')})")
    lines.append("")

    for category in categories:
        lines.extend([f"## {category}", ""])

        for tool_class in tools:
            if category not in (tool_class.categories or [core.GENERAL]):
                continue

            lines.extend([f"### {tool_class.identifier}", ""])
            lines.extend([(tool_class.__doc__ or "").strip() or "*Undocumented*", ""])

            # -- Options are declared on instances, so make one to list them
            tool = tool_class(label=tool_class.identifier, stack=stack)
            for option in tool.options():
                lines.append(f"- **{option.name()}** (default `{option.get(resolved=False)!r}`): {option.description()}")

            lines.append("")

    markdown = "\n".join(lines)

    if filepath:
        with open(filepath, "w") as f:
            f.write(markdown)

    return markdown
