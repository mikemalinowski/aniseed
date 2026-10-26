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

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_dg_node(self):
        node = mref.create("multiplyDivide")
        self.assertIn("DependencyNode", node.assigned_traits())
        self.assertIn("MayaObject", node.assigned_traits())

    def test_api_type(self):
        self.assertEqual(mref.create("transform").api_type(), "kTransform")
        self.assertEqual(mref.create("multiplyDivide").api_type(), "kMultiplyDivide")

    # ------------------------------------------------------------------
    # uuid / exists
    # ------------------------------------------------------------------

    def test_uuid_matches_ls_and_survives_rename(self):
        node = mref.create("transform", name="foo")
        uuid = node.uuid()
        self.assertEqual(uuid, cmds.ls(node.full_name(), uuid=True)[0])
        node.rename("bar")
        self.assertEqual(node.uuid(), uuid)

    def test_exists_false_after_delete(self):
        node = mref.create("multiplyDivide")
        self.assertTrue(node.exists())
        node.delete()
        self.assertFalse(node.exists())

    # ------------------------------------------------------------------
    # is_referenced / reference_node / is_default_node
    # ------------------------------------------------------------------

    def test_is_referenced_false_for_local_node(self):
        node = mref.create("transform")
        self.assertFalse(node.is_referenced())
        self.assertIsNone(node.reference_node())

    def test_referenced_node_reports_reference_node(self):
        import os
        import tempfile

        cmds.createNode("transform", name="ref_me")
        path = os.path.join(tempfile.mkdtemp(), "mref_dependency_ref.ma").replace("\\", "/")
        cmds.file(rename=path)
        cmds.file(save=True, type="mayaAscii", force=True)

        cmds.file(newFile=True, force=True)
        cmds.file(path, reference=True, namespace="ref")

        node = mref.get("ref:ref_me")
        self.assertTrue(node.is_referenced())
        self.assertEqual(node.reference_node().name(), "refRN")

    def test_is_default_node(self):
        self.assertTrue(mref.get("time1").is_default_node())
        self.assertFalse(mref.create("transform").is_default_node())

    # ------------------------------------------------------------------
    # node_namespace / set_node_namespace
    # ------------------------------------------------------------------

    def test_node_namespace_empty_in_root(self):
        node = mref.create("transform", name="foo")
        self.assertEqual(node.node_namespace(), "")

    def test_set_node_namespace_creates_nested_namespace(self):
        node = mref.create("transform", name="foo")
        node.set_node_namespace("char:rig")
        self.assertTrue(cmds.namespace(exists=":char:rig"))
        self.assertEqual(node.name(), "char:rig:foo")
        self.assertEqual(node.node_namespace(), "char:rig")

    def test_set_node_namespace_back_to_root(self):
        node = mref.create("transform", name="foo")
        node.set_node_namespace("ns")
        node.set_node_namespace("")
        self.assertEqual(node.name(), "foo")
        self.assertEqual(node.node_namespace(), "")

    # ------------------------------------------------------------------
    # select / duplicate
    # ------------------------------------------------------------------

    def test_select_replace_and_add(self):
        a = mref.create("transform", name="a")
        b = mref.create("transform", name="b")

        a.select()
        self.assertEqual(cmds.ls(selection=True), ["a"])

        b.select()
        self.assertEqual(cmds.ls(selection=True), ["b"])

        a.select(add=True)
        self.assertEqual(sorted(cmds.ls(selection=True)), ["a", "b"])

    def test_duplicate_dg_node(self):
        node = mref.create("multiplyDivide", name="md")
        copy = node.duplicate(name="md_copy")
        self.assertEqual(copy.name(), "md_copy")
        self.assertEqual(copy.node_type(), "multiplyDivide")
        self.assertNotEqual(copy, node)

    def test_duplicate_dag_node_returns_root(self):
        transform = cmds.polyCube(name="cube")[0]
        copy = mref.get(transform).duplicate()
        self.assertEqual(copy.node_type(), "transform")
        self.assertIsNotNone(copy.shape())

    # ------------------------------------------------------------------
    # node_notes / set_node_notes
    # ------------------------------------------------------------------

    def test_node_notes_empty_by_default(self):
        self.assertEqual(mref.create("transform").node_notes(), "")

    def test_node_notes_round_trip(self):
        node = mref.create("transform")
        node.set_node_notes("hello")
        self.assertEqual(node.node_notes(), "hello")
        self.assertEqual(cmds.getAttr(f"{node.full_name()}.notes"), "hello")

        node.set_node_notes("again")
        self.assertEqual(node.node_notes(), "again")

    # ------------------------------------------------------------------
    # plug_connections
    # ------------------------------------------------------------------

    def test_plug_connections_pairs_are_source_to_destination(self):
        a = mref.create("multiplyDivide", name="a")
        b = mref.create("multiplyDivide", name="b")
        c = mref.create("multiplyDivide", name="c")
        cmds.connectAttr("a.outputX", "b.input1X")
        cmds.connectAttr("b.outputY", "c.input2Y")

        def names(pairs):
            return sorted(
                (src.name(include_node=True), dst.name(include_node=True))
                for src, dst in pairs
            )

        self.assertEqual(
            names(b.plug_connections()),
            [("a.outputX", "b.input1X"), ("b.outputY", "c.input2Y")],
        )
        self.assertEqual(
            names(b.plug_connections(destination=False)),
            [("a.outputX", "b.input1X")],
        )
        self.assertEqual(
            names(b.plug_connections(source=False)),
            [("b.outputY", "c.input2Y")],
        )

    def test_plug_connections_empty_for_unconnected(self):
        self.assertEqual(mref.create("multiplyDivide").plug_connections(), [])

    # ------------------------------------------------------------------
    # history / future
    # ------------------------------------------------------------------

    def test_history_excludes_self_and_filters_type(self):
        transform = cmds.polyCube(name="cube")[0]
        cmds.cluster(transform)
        cube = mref.get(transform)

        history = cube.history()
        self.assertNotIn(cube, history)
        self.assertTrue(any(node.node_type() == "polyCube" for node in history))

        deformers = cube.history(node_type="geometryFilter")
        self.assertEqual([node.node_type() for node in deformers], ["cluster"])

    def test_future(self):
        poly_cube = mref.get(cmds.polyCube(name="cube")[1])

        future = poly_cube.future()
        self.assertNotIn(poly_cube, future)
        self.assertTrue(any(node.node_type() == "mesh" for node in future))
        self.assertEqual(
            [node.node_type() for node in poly_cube.future(node_type="mesh")],
            ["mesh"],
        )


if __name__ == "__main__":
    unittest.main()