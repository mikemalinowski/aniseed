import unittest

import maya.standalone
import mref
from maya import cmds


class TestScriptNode(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_script_node(self, **kwargs):
        return mref.get(cmds.scriptNode(name="script", **kwargs))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_script_node(self):
        self.assertIn("ScriptNode", self._make_script_node().assigned_traits())

    def test_does_not_bind_to_unrelated_node(self):
        node = mref.get(cmds.createNode("multiplyDivide"))
        self.assertNotIn("ScriptNode", node.assigned_traits())

    # ------------------------------------------------------------------
    # scripts
    # ------------------------------------------------------------------

    def test_before_script(self):
        node = self._make_script_node(beforeScript="print 1;")
        self.assertEqual(node.before_script(), "print 1;")
        node.set_before_script("print 2;")
        self.assertEqual(node.before_script(), "print 2;")

    def test_after_script(self):
        node = self._make_script_node()
        self.assertEqual(node.after_script(), "")
        node.set_after_script("print 3;")
        self.assertEqual(node.after_script(), "print 3;")

    # ------------------------------------------------------------------
    # script / source types
    # ------------------------------------------------------------------

    def test_script_type(self):
        node = self._make_script_node(scriptType=2)
        self.assertEqual(node.script_type(), "gui_open_close")

    def test_set_script_type_by_name_and_index(self):
        node = self._make_script_node()
        self.assertEqual(node.script_type(), "demand")

        node.set_script_type("time_changed")
        self.assertEqual(node.script_type(), "time_changed")
        self.assertEqual(cmds.getAttr(f"{node.name()}.scriptType"), 7)

        node.set_script_type(1)
        self.assertEqual(node.script_type(), "open_close")

    def test_set_script_type_invalid(self):
        node = self._make_script_node()
        with self.assertRaises(ValueError):
            node.set_script_type("never")
        with self.assertRaises(ValueError):
            node.set_script_type(99)

    def test_source_type(self):
        self.assertEqual(self._make_script_node().source_type(), "mel")
        self.assertEqual(
            mref.get(cmds.scriptNode(name="py", sourceType="python")).source_type(),
            "python",
        )

    def test_set_source_type(self):
        node = self._make_script_node()
        node.set_source_type("python")
        self.assertEqual(node.source_type(), "python")
        node.set_source_type(0)
        self.assertEqual(node.source_type(), "mel")
        with self.assertRaises(ValueError):
            node.set_source_type("lua")

    # ------------------------------------------------------------------
    # execution
    # ------------------------------------------------------------------

    def test_execute_before(self):
        node = self._make_script_node(beforeScript="createNode transform -n ran_before;")
        self.assertFalse(cmds.objExists("ran_before"))
        node.execute_before()
        self.assertTrue(cmds.objExists("ran_before"))

    def test_execute_after_python(self):
        node = self._make_script_node(
            afterScript="import maya.cmds\nmaya.cmds.createNode('transform', name='ran_after')",
            sourceType="python",
        )
        node.execute_after()
        self.assertTrue(cmds.objExists("ran_after"))


if __name__ == "__main__":
    unittest.main()
