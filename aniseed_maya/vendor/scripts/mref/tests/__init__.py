"""
Test suite for the mref module. Run via :func:`run` to execute every
``test_*.py`` in one pass, or via the top-level :func:`mref.test`
shortcut which delegates here.
"""
import os
import unittest


def run(verbosity: int = 2, target: str = None) -> unittest.TestResult:
    """
    Discover and run the mref test suite.

    WARNING: Each test calls ``cmds.file(newFile=True, force=True)``
    which discards the currently open scene. Save your work first.

    :param verbosity: ``0`` (silent), ``1`` (dots), ``2`` (one line
        per test, the default).
    :param target: Optionally limit the run to a subset. Forms:
        ``"test_mesh"`` (one module),
        ``"test_mesh.TestMesh"`` (one class),
        ``"test_mesh.TestMesh.test_vertex_count"`` (one test).
        When ``None`` (default) every test in the suite runs.
    :return: The ``unittest.TestResult`` from the run.
    """
    loader = unittest.TestLoader()

    if target:
        suite = loader.loadTestsFromName(f"mref.tests.{target}")
    else:
        suite = loader.discover(
            start_dir=os.path.dirname(__file__),
            pattern="test_*.py",
        )

    return unittest.TextTestRunner(verbosity=verbosity).run(suite)