import unittest

import maya.standalone
import mref
from maya import cmds


class TestObjectSet(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_set(self, *members):
        return mref.get(cmds.sets(list(members), name="my_set"))

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_object_set(self):
        object_set = self._make_set()
        self.assertIn("ObjectSet", object_set.assigned_traits())

    def test_binds_to_shading_engine(self):
        self.assertIn("ObjectSet", mref.get("initialShadingGroup").assigned_traits())

    def test_does_not_bind_to_transforms(self):
        self.assertNotIn("ObjectSet", mref.create("transform").assigned_traits())

    # ------------------------------------------------------------------
    # members
    # ------------------------------------------------------------------

    def test_members(self):
        node_a = mref.create("transform", name="node_a")
        node_b = mref.create("transform", name="node_b")
        object_set = self._make_set(node_a.full_name(), node_b.full_name())

        members = object_set.members()
        self.assertIsInstance(members, mref.ReferenceList)
        self.assertEqual(sorted(members.names()), ["node_a", "node_b"])

    def test_members_empty(self):
        self.assertEqual(len(self._make_set().members()), 0)

    def test_component_members_are_strings(self):
        cube = cmds.polyCube(name="cube", constructionHistory=False)[0]
        object_set = self._make_set(f"{cube}.vtx[0:3]")

        members = object_set.members()
        self.assertEqual(len(members), 1)
        self.assertIsInstance(members[0], str)

        self.assertEqual(len(object_set.members(flatten=True)), 4)

    def test_add_and_remove_members(self):
        object_set = self._make_set()
        node_a = mref.create("transform", name="node_a")
        node_b = mref.create("transform", name="node_b")

        object_set.add_members([node_a, node_b.full_name()])
        self.assertEqual(len(object_set.members()), 2)

        object_set.remove_members(node_a)
        self.assertEqual(object_set.members().names(), ["node_b"])

    def test_is_member(self):
        node_a = mref.create("transform", name="node_a")
        node_b = mref.create("transform", name="node_b")
        object_set = self._make_set(node_a.full_name())

        self.assertTrue(object_set.is_member(node_a))
        self.assertFalse(object_set.is_member(node_b))

    def test_clear(self):
        node_a = mref.create("transform", name="node_a")
        object_set = self._make_set(node_a.full_name())
        object_set.clear()
        self.assertEqual(len(object_set.members()), 0)


if __name__ == "__main__":
    unittest.main()
