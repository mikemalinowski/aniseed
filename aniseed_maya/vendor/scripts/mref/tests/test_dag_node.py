import unittest

import maya.standalone
import mref
from maya import cmds
from maya.api import OpenMaya as om


class TestDagNode(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    # ------------------------------------------------------------------
    # full_name
    # ------------------------------------------------------------------

    def test_full_name_returns_dag_path(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform", parent="parent_xform")
        ref = mref.get("|parent_xform|child_xform")
        self.assertEqual(ref.full_name(), "|parent_xform|child_xform")

    # ------------------------------------------------------------------
    # parent / all_parents
    # ------------------------------------------------------------------

    def test_parent_returns_referenceditem(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform", parent="parent_xform")
        ref = mref.get("|parent_xform|child_xform")
        parent = ref.parent()
        self.assertIsInstance(parent, mref.ReferencedItem)
        self.assertEqual(parent.name(), "parent_xform")

    def test_parent_returns_none_at_scene_root(self):
        cmds.createNode("transform", name="root_xform")
        ref = mref.get("root_xform")
        self.assertIsNone(ref.parent())

    def test_all_parents_returns_chain_from_innermost_outward(self):
        cmds.createNode("transform", name="grandparent")
        cmds.createNode("transform", name="parent_xform", parent="grandparent")
        cmds.createNode("transform", name="child_xform", parent="grandparent|parent_xform")

        ref = mref.get("|grandparent|parent_xform|child_xform")
        parents = ref.all_parents()

        self.assertEqual(len(parents), 2)
        self.assertEqual(parents[0].name(), "parent_xform")
        self.assertEqual(parents[1].name(), "grandparent")

    def test_all_parents_empty_at_root(self):
        cmds.createNode("transform", name="root_xform")
        ref = mref.get("root_xform")
        self.assertEqual(ref.all_parents(), [])

    # ------------------------------------------------------------------
    # children
    # ------------------------------------------------------------------

    def test_children_returns_only_immediate_by_default(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform", parent="parent_xform")
        cmds.createNode(
            "transform",
            name="grandchild",
            parent="parent_xform|child_xform",
        )

        ref = mref.get("parent_xform")
        names = [c.name() for c in ref.children()]

        self.assertIn("child_xform", names)
        self.assertNotIn("grandchild", names)

    def test_children_recursive_returns_all_descendants(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform", parent="parent_xform")
        cmds.createNode(
            "transform",
            name="grandchild",
            parent="parent_xform|child_xform",
        )

        ref = mref.get("parent_xform")
        names = [c.name() for c in ref.children(recursive=True)]

        self.assertIn("child_xform", names)
        self.assertIn("grandchild", names)

    def test_children_node_type_filter(self):
        transform = cmds.polyCube(name="cube")[0]
        ref = mref.get(transform)

        meshes = ref.children(node_type="mesh")

        self.assertEqual(len(meshes), 1)

    def test_children_name_match_substring(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="foo_child", parent="parent_xform")
        cmds.createNode("transform", name="bar_child", parent="parent_xform")

        ref = mref.get("parent_xform")
        names = [c.name() for c in ref.children(name_match="foo")]

        self.assertIn("foo_child", names)
        self.assertNotIn("bar_child", names)

    def test_children_include_shapes_default(self):
        transform = cmds.polyCube(name="cube")[0]
        ref = mref.get(transform)

        has_shape = any(
            cmds.objectType(c.full_name(), isAType="shape")
            for c in ref.children()
        )

        self.assertTrue(has_shape)

    def test_children_exclude_shapes(self):
        transform = cmds.polyCube(name="cube")[0]
        ref = mref.get(transform)

        has_shape = any(
            cmds.objectType(c.full_name(), isAType="shape")
            for c in ref.children(include_shapes=False)
        )

        self.assertFalse(has_shape)

    # ------------------------------------------------------------------
    # set_parent
    # ------------------------------------------------------------------

    def test_set_parent_normal(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform")
        ref = mref.get("child_xform")

        ref.set_parent("parent_xform")

        self.assertEqual(ref.parent().name(), "parent_xform")

    def test_set_parent_to_world_with_none(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform", parent="parent_xform")
        ref = mref.get("|parent_xform|child_xform")

        ref.set_parent(None)

        self.assertIsNone(ref.parent())

    def test_set_parent_to_self_is_noop(self):
        cmds.createNode("transform", name="x")
        ref = mref.get("x")

        ref.set_parent(ref)

        self.assertIsNone(ref.parent())

    def test_set_parent_already_parented_is_noop(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform", parent="parent_xform")
        ref = mref.get("|parent_xform|child_xform")

        ref.set_parent("parent_xform")

        self.assertEqual(ref.parent().name(), "parent_xform")

    # ------------------------------------------------------------------
    # add_child / add_children
    # ------------------------------------------------------------------

    def test_add_child(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform")

        parent_ref = mref.get("parent_xform")
        parent_ref.add_child("child_xform")

        names = [c.name() for c in parent_ref.children()]
        self.assertIn("child_xform", names)

    def test_add_child_to_self_is_noop(self):
        cmds.createNode("transform", name="x")
        ref = mref.get("x")

        ref.add_child(ref)

        self.assertEqual(len(ref.children()), 0)

    def test_add_child_already_child_is_noop(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_xform", parent="parent_xform")

        parent_ref = mref.get("parent_xform")
        parent_ref.add_child("|parent_xform|child_xform")

        names = [c.name() for c in parent_ref.children()]
        self.assertEqual(names.count("child_xform"), 1)

    def test_add_children_batched(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="child_a")
        cmds.createNode("transform", name="child_b")
        cmds.createNode("transform", name="child_c")

        parent_ref = mref.get("parent_xform")
        parent_ref.add_children(["child_a", "child_b", "child_c"])

        names = sorted(c.name() for c in parent_ref.children())
        self.assertEqual(names, ["child_a", "child_b", "child_c"])

    def test_add_children_empty_list_is_noop(self):
        cmds.createNode("transform", name="parent_xform")
        parent_ref = mref.get("parent_xform")

        parent_ref.add_children([])

        self.assertEqual(len(parent_ref.children()), 0)

    # ------------------------------------------------------------------
    # shape / shapes
    # ------------------------------------------------------------------

    def test_shape_returns_first_shape(self):
        transform = cmds.polyCube(name="cube")[0]
        ref = mref.get(transform)

        shape = ref.shape()

        self.assertIsNotNone(shape)
        self.assertTrue(cmds.objectType(shape.full_name(), isAType="shape"))

    def test_shape_returns_none_when_no_shape(self):
        cmds.createNode("transform", name="x")
        ref = mref.get("x")

        self.assertIsNone(ref.shape())

    def test_shape_uses_full_path(self):
        transform = cmds.polyCube(name="cube")[0]
        ref = mref.get(transform)

        shape = ref.shape()

        self.assertTrue(shape.full_name().startswith("|"))

    def test_shapes_returns_list_with_shape(self):
        transform = cmds.polyCube(name="cube")[0]
        ref = mref.get(transform)

        shapes = ref.shapes()

        self.assertGreater(len(shapes), 0)

    # ------------------------------------------------------------------
    # constraints
    # ------------------------------------------------------------------

    def test_constraints_returns_referencelist(self):
        target = cmds.createNode("transform", name="target")
        driver = cmds.createNode("transform", name="driver")
        cmds.pointConstraint(driver, target)

        target_ref = mref.get(target)
        constraints = target_ref.constraints()

        self.assertIsInstance(constraints, mref.ReferenceList)
        self.assertGreater(len(constraints), 0)

    def test_constraints_finds_real_constraint_via_inheritance(self):
        target = cmds.createNode("transform", name="target")
        driver = cmds.createNode("transform", name="driver")
        cmds.pointConstraint(driver, target)

        target_ref = mref.get(target)
        constraints = target_ref.constraints()

        self.assertTrue(
            cmds.objectType(constraints[0].full_name(), isAType="constraint")
        )

    def test_constraints_excludes_non_constraint_children(self):
        cmds.createNode("transform", name="parent_xform")
        cmds.createNode("transform", name="not_a_constraint", parent="parent_xform")

        parent_ref = mref.get("parent_xform")

        self.assertEqual(len(parent_ref.constraints()), 0)

    # ------------------------------------------------------------------
    # dag
    # ------------------------------------------------------------------

    def test_dag_returns_mfn_dag_node(self):
        cmds.createNode("transform", name="x")
        ref = mref.get("x")

        self.assertIsInstance(ref.dag(), om.MFnDagNode)


if __name__ == "__main__":
    unittest.main()