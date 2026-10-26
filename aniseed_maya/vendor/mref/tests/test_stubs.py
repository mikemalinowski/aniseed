import ast
import os
import unittest

import maya.standalone
import mref
from maya import cmds
from mref import stubs


_PACKAGE_DIR = os.path.dirname(mref.__file__)
_TYPES_PATH = os.path.join(_PACKAGE_DIR, "types.pyi")
_INIT_PATH = os.path.join(_PACKAGE_DIR, "__init__.pyi")
_REGENERATE = "Re-run mref.generate_stubs(probe=False) to update the stubs."


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class TestStubs(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    # ------------------------------------------------------------------
    # up to date
    # ------------------------------------------------------------------

    def test_stub_files_exist(self):
        self.assertTrue(os.path.exists(_TYPES_PATH), _REGENERATE)
        self.assertTrue(os.path.exists(_INIT_PATH), _REGENERATE)

    def test_trait_stubs_up_to_date(self):
        # -- Fails whenever a trait method is added, removed or changed
        # -- without regenerating the stubs
        self.assertIn(stubs.render_trait_stubs(), _read(_TYPES_PATH), _REGENERATE)

    def test_init_stub_up_to_date(self):
        node_types = stubs.read_stub_probe(_TYPES_PATH)["node_types"]
        self.assertIn(stubs.render_init(node_types), _read(_INIT_PATH), _REGENERATE)

    def test_types_stub_round_trips(self):
        node_types = stubs.read_stub_probe(_TYPES_PATH)["node_types"]
        self.assertIn(stubs.render_types(node_types), _read(_TYPES_PATH))

    def test_every_trait_has_a_stub_class(self):
        classes = {
            node.name
            for node in ast.parse(_read(_TYPES_PATH)).body
            if isinstance(node, ast.ClassDef)
        }
        for trait in mref.TraitLibrary.singleton().plugins():
            self.assertIn(f"{trait.__name__}Trait", classes, _REGENERATE)

    # ------------------------------------------------------------------
    # node type mapping
    # ------------------------------------------------------------------

    def test_node_classes_match_runtime_traits(self):
        # -- A new trait or a can_bind change needs a full probe
        node_types = stubs.read_stub_probe(_TYPES_PATH)["node_types"]
        message = "Re-run mref.generate_stubs() (with probe) to update the stubs."

        cube = cmds.polyCube(constructionHistory=False)[0]
        joint = cmds.createNode("joint")
        nodes = [
            cmds.listRelatives(cube, shapes=True, fullPath=True)[0],
            joint,
            cmds.skinCluster(joint, cube)[0],
            cmds.cluster(cube)[0],
            cmds.createNode("lambert"),
            cmds.createNode("pointLight"),
            cmds.createNode("multMatrix"),
            cmds.sets(empty=True),
        ]

        for node in nodes:
            item = mref.get(node)
            node_type = cmds.nodeType(node)
            self.assertIn(node_type, node_types, message)
            self.assertEqual(
                sorted(node_types[node_type]),
                sorted(item.assigned_traits()),
                f"{node_type}: {message}",
            )

    def test_node_class_name(self):
        self.assertEqual(stubs.node_class_name("mesh"), "MeshNode")
        self.assertEqual(stubs.node_class_name("aiStandardSurface"), "AiStandardSurfaceNode")

    # ------------------------------------------------------------------
    # init stub
    # ------------------------------------------------------------------

    def test_init_stub_covers_public_names(self):
        tree = ast.parse(_read(_INIT_PATH))
        declared = set()
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                declared.update(alias.asname or alias.name for alias in node.names)
            elif isinstance(node, ast.FunctionDef):
                declared.add(node.name)

        for name in stubs.public_init_names():
            self.assertIn(name, declared, _REGENERATE)

    # ------------------------------------------------------------------
    # runtime types module
    # ------------------------------------------------------------------

    def test_runtime_types_resolve_to_referenced_item(self):
        self.assertIs(mref.types.MeshNode, mref.ReferencedItem)
        self.assertIs(mref.types.MeshTrait, mref.ReferencedItem)
        self.assertIs(mref.types.Attribute, mref.ReferencedItem)

    def test_runtime_types_unknown_name_raises(self):
        with self.assertRaises(AttributeError):
            mref.types.not_a_type


if __name__ == "__main__":
    unittest.main()
