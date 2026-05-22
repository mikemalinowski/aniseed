import unittest

import maya.standalone
import mref
from maya import cmds
from mref.core import ReferencedItem


class TestGetMplug(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    # --------------------------------------------------------------
    # Direct / compound / array attribute resolution
    # --------------------------------------------------------------

    def test_direct_attribute(self):
        cmds.createNode("transform", name="foo")
        plug = ReferencedItem.get_mplug("foo.translateX")
        self.assertEqual(plug.partialName(useLongNames=True), "translateX")

    def test_compound_attribute(self):
        cmds.createNode("transform", name="foo")
        plug = ReferencedItem.get_mplug("foo.translate.translateX")
        self.assertEqual(plug.partialName(useLongNames=True), "translateX")

    def test_array_attribute_element(self):
        cmds.createNode("multiplyDivide", name="md")
        # input1 itself is compound; use a known array-of-compound attribute
        # instead — addAttr a custom array attr to exercise the array path
        # without relying on input1's exact shape.
        cmds.addAttr(
            "md",
            longName="weights",
            attributeType="double",
            multi=True,
        )
        cmds.setAttr("md.weights[3]", 0.5)

        plug = ReferencedItem.get_mplug("md.weights[3]")
        self.assertTrue(plug.isElement)
        self.assertEqual(plug.logicalIndex(), 3)

    # --------------------------------------------------------------
    # Alias resolution (the most fragile branch)
    # --------------------------------------------------------------

    def test_blendshape_alias_resolution(self):
        base = cmds.polyCube(name="base")[0]
        target = cmds.polyCube(name="target")[0]
        bs = cmds.blendShape(base, name="bs")[0]
        cmds.blendShape(bs, edit=True, target=(base, 0, target, 1.0))
        cmds.aliasAttr("smile", f"{bs}.weight[0]")

        plug = ReferencedItem.get_mplug(f"{bs}.smile")

        # Whether the fast path or the manual alias path resolved it,
        # the resulting plug must refer to weight[0] on the blendshape.
        self.assertTrue(plug.isElement)
        self.assertEqual(plug.logicalIndex(), 0)

    # --------------------------------------------------------------
    # Error paths
    # --------------------------------------------------------------

    def test_not_an_attribute_raises(self):
        with self.assertRaises(RuntimeError):
            ReferencedItem.get_mplug("foo")

    def test_unknown_attribute_raises(self):
        cmds.createNode("transform", name="foo")
        with self.assertRaises(RuntimeError):
            ReferencedItem.get_mplug("foo.nonexistent_attribute")

    # --------------------------------------------------------------
    # Hash invariants for MPlug-backed ReferencedItems
    # --------------------------------------------------------------

    def test_mplug_referenced_items_compare_equal(self):
        cmds.createNode("transform", name="foo")
        ref_a = mref.get("foo.translateX")
        ref_b = mref.get("foo.translateX")
        self.assertEqual(ref_a, ref_b)
        self.assertEqual(hash(ref_a), hash(ref_b))

    def test_mplug_hash_stable_across_owner_rename(self):
        cmds.createNode("transform", name="foo")
        ref = mref.get("foo.translateX")

        hash_before = hash(ref)
        cmds.rename("foo", "bar")
        hash_after = hash(ref)

        self.assertEqual(
            hash_before,
            hash_after,
            "hash(MPlug-backed ReferencedItem) must survive node rename",
        )

    def test_mplug_referenced_items_work_in_a_set(self):
        cmds.createNode("transform", name="foo")
        ref_a = mref.get("foo.translateX")
        ref_b = mref.get("foo.translateX")

        plugs = {ref_a}
        self.assertIn(ref_b, plugs)

        cmds.rename("foo", "bar")
        self.assertIn(ref_a, plugs)


if __name__ == "__main__":
    unittest.main()