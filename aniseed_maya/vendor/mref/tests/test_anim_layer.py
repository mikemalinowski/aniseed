import unittest

import maya.standalone
import mref
from maya import cmds


class TestAnimLayer(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

        self.node = cmds.createNode("transform", name="ctrl")

    def _make_layer(self, name="layer", **kwargs):
        return mref.get(cmds.animLayer(name, **kwargs))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_anim_layer(self):
        layer = self._make_layer()
        self.assertIn("AnimLayer", layer.assigned_traits())
        self.assertIn("ObjectSet", layer.assigned_traits())

    def test_does_not_bind_to_object_set(self):
        object_set = mref.get(cmds.sets(name="a_set", empty=True))
        self.assertNotIn("AnimLayer", object_set.assigned_traits())

    # ------------------------------------------------------------------
    # weight / mute / solo / lock / override
    # ------------------------------------------------------------------

    def test_weight(self):
        layer = self._make_layer()
        self.assertAlmostEqual(layer.weight(), 1.0)
        layer.set_weight(0.25)
        self.assertAlmostEqual(layer.weight(), 0.25)

    def test_mute(self):
        layer = self._make_layer()
        self.assertFalse(layer.is_muted())
        layer.set_muted(True)
        self.assertTrue(layer.is_muted())
        layer.set_muted(False)
        self.assertFalse(layer.is_muted())

    def test_solo(self):
        layer = self._make_layer()
        self.assertFalse(layer.is_solo())
        layer.set_solo(True)
        self.assertTrue(layer.is_solo())

    def test_layer_lock_is_not_node_lock(self):
        layer = self._make_layer()
        self.assertFalse(layer.is_layer_locked())
        layer.set_layer_locked(True)
        self.assertTrue(layer.is_layer_locked())
        self.assertFalse(layer.is_locked())

    def test_override(self):
        layer = self._make_layer()
        self.assertFalse(layer.is_override())
        layer.set_override(True)
        self.assertTrue(layer.is_override())

    # ------------------------------------------------------------------
    # hierarchy
    # ------------------------------------------------------------------

    def test_is_base_layer(self):
        layer = self._make_layer()
        base = mref.get(cmds.animLayer(query=True, root=True))
        self.assertTrue(base.is_base_layer())
        self.assertFalse(layer.is_base_layer())

    def test_parent_layer(self):
        parent = self._make_layer("parent_layer")
        child = self._make_layer("child_layer", parent=parent.name())
        self.assertEqual(child.parent_layer(), parent)
        self.assertTrue(parent.parent_layer().is_base_layer())
        self.assertIsNone(parent.parent_layer().parent_layer())

    def test_child_layers(self):
        parent = self._make_layer("parent_layer")
        self._make_layer("child_a", parent=parent.name())
        self._make_layer("child_b", parent=parent.name())
        children = parent.child_layers()
        self.assertIsInstance(children, mref.ReferenceList)
        self.assertEqual(sorted(children.names()), ["child_a", "child_b"])
        self.assertEqual(len(mref.get("child_a").child_layers()), 0)

    # ------------------------------------------------------------------
    # attributes
    # ------------------------------------------------------------------

    def test_layered_attributes_empty(self):
        self.assertEqual(len(self._make_layer().layered_attributes()), 0)

    def test_add_layered_attributes(self):
        layer = self._make_layer()
        layer.add_layered_attributes(f"{self.node}.translateX")
        layer.add_layered_attributes([mref.get(f"{self.node}.rotateY")])

        attributes = layer.layered_attributes()
        self.assertIsInstance(attributes, mref.ReferenceList)
        names = sorted(attribute.name(include_node=True) for attribute in attributes)
        self.assertEqual(len(names), 2)
        self.assertTrue(any(name.startswith("ctrl.t") for name in names))
        self.assertTrue(any(name.startswith("ctrl.r") for name in names))

    def test_remove_layered_attributes(self):
        layer = self._make_layer()
        layer.add_layered_attributes([f"{self.node}.translateX", f"{self.node}.translateY"])
        layer.remove_layered_attributes(f"{self.node}.translateX")

        attributes = layer.layered_attributes()
        self.assertEqual(len(attributes), 1)
        self.assertEqual(attributes[0].pointer(), mref.get(f"{self.node}.translateY").pointer())


if __name__ == "__main__":
    unittest.main()
