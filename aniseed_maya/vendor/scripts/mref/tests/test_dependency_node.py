import unittest

import maya.standalone
import mref
from maya import cmds


class TestDependencyNode(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    # ------------------------------------------------------------------
    # __getattr__
    # ------------------------------------------------------------------

    def test_getattr_returns_attribute_for_known_name(self):
        node = mref.create("transform")
        attr = node.translateX
        self.assertIsInstance(attr, mref.ReferencedItem)

    def test_getattr_raises_attribute_error_for_unknown_name(self):
        node = mref.create("transform")
        with self.assertRaises(AttributeError):
            node.this_attribute_does_not_exist

    # ------------------------------------------------------------------
    # attribute / attr / has_attribute
    # ------------------------------------------------------------------

    def test_attribute_returns_referenceditem_for_known(self):
        node = mref.create("transform")
        result = node.attribute("translateX")
        self.assertIsInstance(result, mref.ReferencedItem)

    def test_attribute_returns_none_for_unknown(self):
        node = mref.create("transform")
        self.assertIsNone(node.attribute("nonsense"))

    def test_attr_is_alias_for_attribute(self):
        node = mref.create("transform")
        self.assertIsNotNone(node.attr("translateX"))

    def test_has_attribute_true_for_known(self):
        node = mref.create("transform")
        self.assertTrue(node.has_attribute("translateX"))

    def test_has_attribute_false_for_unknown(self):
        node = mref.create("transform")
        self.assertFalse(node.has_attribute("nonsense"))

    # ------------------------------------------------------------------
    # add_attribute
    # ------------------------------------------------------------------

    def test_add_attribute_creates_and_initialises(self):
        node = mref.create("transform")
        node.add_attribute("myFloat", 0.5, "float")
        self.assertAlmostEqual(
            cmds.getAttr(f"{node.full_name()}.myFloat"),
            0.5,
        )

    def test_add_attribute_with_none_leaves_default(self):
        node = mref.create("transform")
        node.add_attribute("myFloat", None, "float", defaultValue=2.5)
        self.assertAlmostEqual(
            cmds.getAttr(f"{node.full_name()}.myFloat"),
            2.5,
        )

    def test_add_attribute_compound_raises(self):
        node = mref.create("transform")
        with self.assertRaises(KeyError):
            node.add_attribute("myCompound", None, "compound")

    # ------------------------------------------------------------------
    # attributes
    # ------------------------------------------------------------------

    def test_attributes_returns_non_empty_list(self):
        node = mref.create("transform")
        attrs = node.attributes()
        self.assertIsInstance(attrs, list)
        self.assertGreater(len(attrs), 0)

    # ------------------------------------------------------------------
    # node_type / rename / delete
    # ------------------------------------------------------------------

    def test_node_type(self):
        node = mref.create("multiplyDivide")
        self.assertEqual(node.node_type(), "multiplyDivide")

    def test_rename(self):
        node = mref.create("transform", name="foo")
        node.rename("bar")
        self.assertEqual(node.name(), "bar")

    def test_delete_removes_node(self):
        node = mref.create("transform", name="to_delete")
        self.assertTrue(cmds.objExists("to_delete"))
        node.delete()
        self.assertFalse(cmds.objExists("to_delete"))

    # ------------------------------------------------------------------
    # inputs / outputs (shapes override path)
    # ------------------------------------------------------------------

    def test_inputs_returns_list(self):
        node = mref.create("multiplyDivide")
        self.assertIsInstance(node.inputs(), list)

    def test_outputs_returns_list(self):
        node = mref.create("multiplyDivide")
        self.assertIsInstance(node.outputs(), list)

    def test_inputs_accepts_shapes_override(self):
        node = mref.create("multiplyDivide")
        # Was previously a TypeError because `shapes=True` was hardcoded.
        self.assertIsInstance(node.inputs(shapes=False), list)

    def test_outputs_accepts_shapes_override(self):
        node = mref.create("multiplyDivide")
        self.assertIsInstance(node.outputs(shapes=False), list)

    # ------------------------------------------------------------------
    # lock / unlock / is_locked / set_lock_state (node-level)
    # ------------------------------------------------------------------

    def test_lock_unlock_round_trip(self):
        node = mref.create("transform")
        self.assertFalse(node.is_locked())
        node.lock()
        self.assertTrue(node.is_locked())
        node.unlock()
        self.assertFalse(node.is_locked())

    def test_set_lock_state_round_trip(self):
        node = mref.create("transform")
        node.set_lock_state(True)
        self.assertTrue(node.is_locked())
        node.set_lock_state(False)
        self.assertFalse(node.is_locked())

    # ------------------------------------------------------------------
    # lock_attributes / unlock_attributes (attribute-level)
    # ------------------------------------------------------------------

    def test_lock_attributes_round_trip(self):
        node = mref.create("transform")
        names = ["translateX", "translateY"]

        node.lock_attributes(names)
        for name in names:
            self.assertTrue(
                cmds.getAttr(f"{node.full_name()}.{name}", lock=True),
                f"{name} should be locked",
            )

        node.unlock_attributes(names)
        for name in names:
            self.assertFalse(
                cmds.getAttr(f"{node.full_name()}.{name}", lock=True),
                f"{name} should be unlocked",
            )

    def test_lock_attributes_raises_on_unknown_name(self):
        node = mref.create("transform")
        with self.assertRaises(AttributeError):
            node.lock_attributes(["definitelyNotAnAttribute"])

    def test_unlock_attributes_raises_on_unknown_name(self):
        node = mref.create("transform")
        with self.assertRaises(AttributeError):
            node.unlock_attributes(["definitelyNotAnAttribute"])

    # ------------------------------------------------------------------
    # lock_transform_attributes
    # ------------------------------------------------------------------

    def test_lock_transform_attributes_locks_all_nine(self):
        node = mref.create("transform")
        node.lock_transform_attributes()

        for channel in ["t", "r", "s"]:
            for axis in ["x", "y", "z"]:
                self.assertTrue(
                    cmds.getAttr(f"{node.full_name()}.{channel}{axis}", lock=True),
                    f"{channel}{axis} should be locked",
                )


if __name__ == "__main__":
    unittest.main()