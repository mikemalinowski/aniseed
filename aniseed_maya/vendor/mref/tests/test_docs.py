import os
import tempfile
import unittest

import maya.standalone
import mref
from mref import documentation, stubs


_REGENERATE = "Re-run mref.generate_stubs(probe=False) to update the docs."


class TestDocs(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass

    def _node_types(self):
        return stubs.read_stub_probe(documentation.types_stub_path())["node_types"]

    # ------------------------------------------------------------------
    # up to date
    # ------------------------------------------------------------------

    def test_docs_exist(self):
        path = os.path.join(documentation.default_docs_dir(), "index.html")
        self.assertTrue(os.path.exists(path), _REGENERATE)

    def test_docs_up_to_date(self):
        # -- Fails whenever a trait, method or docstring changes without
        # -- regenerating the docs
        path = os.path.join(documentation.default_docs_dir(), "index.html")
        self.assertEqual(
            documentation.read_page_data(path),
            documentation.build_data(self._node_types()),
            _REGENERATE,
        )

    # ------------------------------------------------------------------
    # content
    # ------------------------------------------------------------------

    def test_every_trait_is_documented(self):
        data = documentation.build_data(self._node_types())
        for trait in mref.TraitLibrary.singleton().plugins():
            self.assertIn(trait.__name__, data["traits"])

    def test_methods_have_signatures_and_source(self):
        mesh = documentation.build_data(self._node_types())["traits"]["Mesh"]
        methods = {method["name"]: method for method in mesh["methods"]}

        self.assertEqual(mesh["binds"], ["kMesh"])
        self.assertEqual(mesh["priority"], 1)
        self.assertEqual(mesh["file"], "mref/traits/mesh.py")

        # -- self is dropped, defaults and annotations are kept
        self.assertEqual(
            methods["vertex_positions"]["signature"],
            "(space: str='object') -> list[list[float]]",
        )
        self.assertIn("x, y, z", methods["vertex_positions"]["doc"])

    def test_private_and_binding_methods_are_excluded(self):
        data = documentation.build_data(self._node_types())
        for trait in data["traits"].values():
            for method in trait["methods"]:
                self.assertFalse(method["name"].startswith("_"))
                self.assertNotEqual(method["name"], "can_bind")

    def test_node_types_list_traits_in_resolution_order(self):
        node = documentation.build_data(self._node_types())["node_types"]["mesh"]
        self.assertEqual(node["class_name"], "MeshNode")
        self.assertEqual(node["traits"][0], "Mesh")
        self.assertEqual(node["traits"][-1], "DependencyNode")

    def test_page_round_trips_data(self):
        data = documentation.build_data(self._node_types())
        directory = tempfile.mkdtemp()
        path = documentation.generate_docs(output_dir=directory)
        self.assertEqual(documentation.read_page_data(path), data)

        with open(path, encoding="utf-8") as handle:
            page = handle.read()
        self.assertNotIn("<!-- MREF_DATA -->", page)
        self.assertIn('id="mref-data"', page)


if __name__ == "__main__":
    unittest.main()
