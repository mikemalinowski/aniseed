import os
import shutil
import tempfile
import unittest

import maya.standalone
import mref
from maya import cmds


class TestReference(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

        self.directory = tempfile.mkdtemp()

        # -- inner.ma holds a single cube, outer.ma references inner.ma
        self.inner_path = self._save_scene("inner.ma", lambda: cmds.polyCube(name="box"))
        self.alt_path = self._save_scene("alt.ma", lambda: cmds.polySphere(name="ball"))
        self.outer_path = self._save_scene(
            "outer.ma",
            lambda: cmds.file(self.inner_path, reference=True, namespace="inner"),
        )
        cmds.file(newFile=True, force=True)

    def tearDown(self):
        cmds.file(newFile=True, force=True)
        shutil.rmtree(self.directory, ignore_errors=True)

    def _save_scene(self, file_name, build):
        cmds.file(newFile=True, force=True)
        build()
        path = os.path.join(self.directory, file_name).replace("\\", "/")
        cmds.file(rename=path)
        cmds.file(save=True, type="mayaAscii")
        return path

    def _reference(self, path, namespace):
        # -- cmds.file returns the (copy-numbered) path of the new
        # -- reference, which uniquely identifies its reference node
        new_path = cmds.file(path, reference=True, namespace=namespace)
        return mref.get(cmds.referenceQuery(new_path, referenceNode=True))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_reference_node(self):
        reference = self._reference(self.inner_path, "a")
        self.assertIn("Reference", reference.assigned_traits())

    def test_does_not_bind_to_transform(self):
        node = mref.get(cmds.createNode("transform"))
        self.assertNotIn("Reference", node.assigned_traits())

    def test_does_not_bind_to_bookkeeping_reference_nodes(self):
        for name in ("sharedReferenceNode", "_UNKNOWN_REF_NODE_"):
            node = mref.get(cmds.createNode("reference", name=name))
            self.assertNotIn("Reference", node.assigned_traits())
            self.assertIn("DependencyNode", node.assigned_traits())

    # ------------------------------------------------------------------
    # file_path / namespace
    # ------------------------------------------------------------------

    def test_file_path(self):
        reference = self._reference(self.inner_path, "a")
        self.assertEqual(os.path.normcase(reference.file_path()), os.path.normcase(self.inner_path))

    def test_file_path_copy_number(self):
        self._reference(self.inner_path, "a")
        second = self._reference(self.inner_path, "b")
        self.assertTrue(second.file_path(copy_number=True).endswith("inner.ma{1}"))
        self.assertTrue(second.file_path().endswith("inner.ma"))

    def test_file_path_unresolved(self):
        reference = self._reference(self.inner_path, "a")
        self.assertTrue(reference.file_path(resolved=False).endswith("inner.ma"))

    def test_namespace(self):
        outer = self._reference(self.outer_path, "out")
        nested = outer.child_references()[0]
        self.assertEqual(outer.namespace(), "out")
        self.assertEqual(nested.namespace(), "out:inner")
        self.assertEqual(nested.namespace(short=True), "inner")

    # ------------------------------------------------------------------
    # loading
    # ------------------------------------------------------------------

    def test_is_loaded_unload_load(self):
        reference = self._reference(self.inner_path, "a")
        self.assertTrue(reference.is_loaded())

        reference.unload()
        self.assertFalse(reference.is_loaded())
        self.assertFalse(cmds.objExists("a:box"))

        # -- Calling again must be a no-op rather than an error
        reference.unload()

        reference.load()
        self.assertTrue(reference.is_loaded())
        self.assertTrue(cmds.objExists("a:box"))
        reference.load()

    def test_reload_picks_up_changes(self):
        reference = self._reference(self.inner_path, "a")
        self.assertTrue(cmds.objExists("a:box"))

        # -- Change the referenced file on disk behind Maya's back
        shutil.copyfile(self.alt_path, self.inner_path)

        reference.reload()
        self.assertTrue(cmds.objExists("a:ball"))
        self.assertFalse(cmds.objExists("a:box"))

    def test_reload_loads_unloaded_reference(self):
        reference = self._reference(self.inner_path, "a")
        reference.unload()
        reference.reload()
        self.assertTrue(reference.is_loaded())
        self.assertTrue(cmds.objExists("a:box"))

    def test_replace_file(self):
        reference = self._reference(self.inner_path, "a")
        reference.replace_file(self.alt_path)
        self.assertTrue(reference.file_path().endswith("alt.ma"))
        self.assertTrue(cmds.objExists("a:ball"))
        self.assertFalse(cmds.objExists("a:box"))
        self.assertEqual(reference.namespace(), "a")

    # ------------------------------------------------------------------
    # contents / hierarchy
    # ------------------------------------------------------------------

    def test_contained_nodes(self):
        reference = self._reference(self.inner_path, "a")
        nodes = reference.contained_nodes()
        self.assertIsInstance(nodes, mref.ReferenceList)
        self.assertIn("a:box", nodes.names())

    def test_contained_nodes_empty_when_unloaded(self):
        reference = self._reference(self.inner_path, "a")
        reference.unload()
        self.assertEqual(len(reference.contained_nodes()), 0)

    def test_parent_and_child_references(self):
        outer = self._reference(self.outer_path, "out")
        self.assertIsNone(outer.parent_reference())

        children = outer.child_references()
        self.assertIsInstance(children, mref.ReferenceList)
        self.assertEqual(len(children), 1)
        self.assertIn("Reference", children[0].assigned_traits())
        self.assertEqual(children[0].parent_reference(), outer)
        self.assertEqual(len(children[0].child_references()), 0)

    def test_remove(self):
        reference = self._reference(self.inner_path, "a")
        name = reference.name()
        reference.remove()
        self.assertFalse(cmds.objExists(name))
        self.assertFalse(cmds.objExists("a:box"))


if __name__ == "__main__":
    unittest.main()
