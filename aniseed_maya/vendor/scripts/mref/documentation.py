"""
Generates the HTML API documentation for mref.

The docs are a single self-contained page (``docs/index.html`` in the
repository) with a page per trait and per Maya node type, listing every
method with its signature, docstring and the trait it comes from.

They are built from the trait source files, using the node type to trait
mapping recorded in ``types.pyi``, so re-run :func:`generate_docs` (or
``mref.generate_stubs()``, which calls it) whenever a trait is added or
extended.
"""
import ast
import inspect
import json
import os
import re

from . import stubs

# -- Marks the script tag the page reads its data from. The tests read the
# -- same block back to check the docs are up to date.
_DATA_OPEN = '<script id="mref-data" type="application/json">'
_DATA_CLOSE = "</script>"


def generate_docs(output_dir: str = None) -> str:
    """
    Regenerates the HTML documentation and returns the path written.

    The node type to trait mapping is read from ``types.pyi``, so after
    adding a trait (or changing a ``can_bind``) run ``mref.generate_stubs()``
    instead, which probes the node types and then calls this.

    :param output_dir: Folder to write ``index.html`` into. Defaults to
        the ``docs`` folder at the root of the mref repository.
    """
    node_types = stubs.read_stub_probe(types_stub_path())["node_types"]

    output_dir = output_dir or default_docs_dir()
    os.makedirs(output_dir, exist_ok=True)

    path = os.path.join(output_dir, "index.html")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_page(build_data(node_types)))

    return path


def default_docs_dir() -> str:
    """
    Returns the ``docs`` folder at the root of the mref repository. The
    package path is resolved first, so a package linked into Maya's
    site-packages still writes into the repository.
    """
    import mref
    package_dir = os.path.realpath(os.path.dirname(mref.__file__))
    return os.path.join(os.path.dirname(package_dir), "docs")


def types_stub_path() -> str:
    import mref
    return os.path.join(os.path.dirname(mref.__file__), "types.pyi")


# ------------------------------------------------------------------------------
# Data
# ------------------------------------------------------------------------------
def build_data(node_types: dict) -> dict:
    """
    Returns everything the page displays: each trait's description,
    binding, priority and methods, and the traits bound to each node type
    (highest priority first).
    """
    import mref

    traits = dict()
    for trait in sorted(mref.TraitLibrary.singleton().plugins(), key=lambda t: t.__name__):
        class_node = _class_node(trait)
        traits[trait.__name__] = dict(
            priority=trait.priority,
            file="mref/traits/" + os.path.basename(inspect.getsourcefile(trait)),
            binds=_binds(class_node),
            doc=ast.get_docstring(class_node) or "",
            methods=[
                _method_data(node)
                for node in class_node.body
                if isinstance(node, ast.FunctionDef)
                and not node.name.startswith("_")
                and node.name not in ("can_bind", "dynamic_function")
            ],
        )

    return dict(
        traits=traits,
        node_types={
            node_type: dict(
                class_name=stubs.node_class_name(node_type),
                traits=trait_names,
            )
            for node_type, trait_names in sorted(node_types.items())
        },
        core=[
            _method_data(node)
            for node in _class_node(mref.ReferencedItem).body
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        ],
    )


def _method_data(node: ast.FunctionDef) -> dict:
    """
    Returns the name, signature and docstring of a method definition.
    The ``self`` / ``cls`` argument is left out of the signature.
    """
    arguments = node.args
    positional = arguments.posonlyargs + arguments.args
    decorators = [ast.unparse(decorator) for decorator in node.decorator_list]

    if positional and "staticmethod" not in decorators:
        # -- Defaults line up with the end of the positional arguments, so
        # -- self / cls only has a default when every positional one does
        defaults = arguments.defaults
        if len(defaults) == len(positional):
            defaults = defaults[1:]

        arguments = ast.arguments(
            posonlyargs=arguments.posonlyargs[1:],
            args=arguments.args if arguments.posonlyargs else arguments.args[1:],
            vararg=arguments.vararg,
            kwonlyargs=arguments.kwonlyargs,
            kw_defaults=arguments.kw_defaults,
            kwarg=arguments.kwarg,
            defaults=defaults,
        )

    signature = f"({ast.unparse(arguments)})"
    if node.returns is not None:
        signature += f" -> {ast.unparse(node.returns)}"

    return dict(
        name=node.name,
        signature=signature,
        doc=ast.get_docstring(node) or "",
        kind=next((d for d in decorators if d in ("classmethod", "staticmethod", "property")), ""),
    )


def _binds(class_node: ast.ClassDef) -> list[str]:
    """
    Returns the ``MFn`` constants a trait's ``can_bind`` checks for.
    """
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == "can_bind":
            return sorted(set(re.findall(r"MFn\.(k\w+)", ast.unparse(node))))
    return []


def _class_node(cls) -> ast.ClassDef:
    with open(inspect.getsourcefile(cls), encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == cls.__name__:
            return node
    raise RuntimeError(f"Could not find the definition of {cls.__name__}")


# ------------------------------------------------------------------------------
# Page
# ------------------------------------------------------------------------------
def render_page(data: dict) -> str:
    """
    Returns the HTML page with the given data embedded in it.
    """
    template_path = os.path.join(os.path.dirname(__file__), "documentation_template.html")
    with open(template_path, encoding="utf-8") as handle:
        template = handle.read()

    # -- "</" would end the script block early; "<\/" is the same JSON
    payload = json.dumps(data, indent=1, sort_keys=True).replace("</", "<\\/")
    block = f"{_DATA_OPEN}\n{payload}\n{_DATA_CLOSE}"
    return template.replace("<!-- MREF_DATA -->", block)


def read_page_data(path: str) -> dict:
    """
    Returns the data embedded in a generated docs page.
    """
    with open(path, encoding="utf-8") as handle:
        content = handle.read()

    start = content.index(_DATA_OPEN) + len(_DATA_OPEN)
    end = content.index(_DATA_CLOSE, start)
    return json.loads(content[start:end])
