import unittest

import maya.standalone
import mref
from maya import cmds
from maya.api import OpenMaya as om


class TestJoint(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_chain(self):
        cmds.select(clear=True)
        a = cmds.joint(name="jnt_a", position=(0, 0, 0))
        b = cmds.joint(name="jnt_b", position=(2, 0, 0))
        c = cmds.joint(name="jnt_c", position=(2, 2, 0))
        cmds.select(clear=True)
        return mref.get(a), mref.get(b), mref.get(c)

    @staticmethod
    def _world_matrix(item):
        return om.MDagPath.getAPathTo(item.pointer()).inclusiveMatrix()

    @staticmethod
    def _world_position(item):
        return cmds.xform(item.full_name(), query=True, worldSpace=True, translation=True)

    def _assert_vectors_equal(self, a, b, places=4):
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, places=places)

    def _axis(self, item, index):
        matrix = self._world_matrix(item)
        return om.MVector(matrix[index * 4], matrix[index * 4 + 1], matrix[index * 4 + 2]).normal()

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_joint(self):
        a, _, _ = self._make_chain()
        self.assertIn("Joint", a.assigned_traits())
        self.assertIn("Transform", a.assigned_traits())

    def test_does_not_bind_to_transform(self):
        node = mref.get(cmds.createNode("transform"))
        self.assertNotIn("Joint", node.assigned_traits())

    # ------------------------------------------------------------------
    # attribute accessors
    # ------------------------------------------------------------------

    def test_joint_orient_round_trip(self):
        a, _, _ = self._make_chain()
        a.set_joint_orient([10.0, 20.0, 30.0])
        self._assert_vectors_equal(a.joint_orient(), [10.0, 20.0, 30.0])

    def test_preferred_angle_round_trip(self):
        a, _, _ = self._make_chain()
        a.set_preferred_angle([0.0, 0.0, 45.0])
        self._assert_vectors_equal(a.preferred_angle(), [0.0, 0.0, 45.0])

    def test_set_preferred_angle_from_current_rotation(self):
        a, _, _ = self._make_chain()
        cmds.setAttr(f"{a.full_name()}.rotate", 5, 15, 25)
        a.set_preferred_angle()
        self._assert_vectors_equal(a.preferred_angle(), [5.0, 15.0, 25.0])

    def test_segment_scale_compensate_round_trip(self):
        a, _, _ = self._make_chain()
        self.assertTrue(a.segment_scale_compensate())
        a.set_segment_scale_compensate(False)
        self.assertFalse(a.segment_scale_compensate())

    def test_radius_round_trip(self):
        a, _, _ = self._make_chain()
        a.set_radius(2.5)
        self.assertAlmostEqual(a.radius(), 2.5)

    # ------------------------------------------------------------------
    # hierarchy
    # ------------------------------------------------------------------

    def test_parent_joint(self):
        a, b, _ = self._make_chain()
        self.assertEqual(b.parent_joint(), a)
        self.assertIsNone(a.parent_joint())

    def test_parent_joint_ignores_non_joint_parent(self):
        a, _, _ = self._make_chain()
        group = cmds.createNode("transform", name="grp")
        cmds.parent(a.full_name(), group)
        self.assertIsNone(a.parent_joint())

    def test_child_joints(self):
        a, b, c = self._make_chain()
        cmds.createNode("transform", name="not_a_joint", parent=a.full_name())
        children = a.child_joints()
        self.assertIsInstance(children, mref.ReferenceList)
        self.assertEqual(list(children), [b])

    def test_child_joints_recursive(self):
        a, b, c = self._make_chain()
        self.assertEqual(list(a.child_joints(recursive=True)), [b, c])

    def test_chain_to(self):
        a, b, c = self._make_chain()
        chain = a.chain_to(c)
        self.assertIsInstance(chain, mref.ReferenceList)
        self.assertEqual(list(chain), [a, b, c])

    def test_chain_to_self(self):
        a, _, _ = self._make_chain()
        self.assertEqual(list(a.chain_to(a)), [a])

    def test_chain_to_accepts_string(self):
        a, b, _ = self._make_chain()
        self.assertEqual(list(a.chain_to("jnt_b")), [a, b])

    def test_chain_to_non_descendant_raises(self):
        a, b, c = self._make_chain()
        with self.assertRaises(ValueError):
            c.chain_to(a)

    # ------------------------------------------------------------------
    # orientation
    # ------------------------------------------------------------------

    def test_orient_to_child_aims_axis(self):
        a, b, c = self._make_chain()
        # -- Rotate jnt_a away so there's real work to do
        a.set_joint_orient([30.0, 40.0, 50.0])
        cmds.setAttr(f"{a.full_name()}.rotate", 10, 0, 0)
        b_pos = self._world_position(b)
        c_pos = self._world_position(c)

        a.orient_to_child()

        # -- Children have not moved
        self._assert_vectors_equal(self._world_position(b), b_pos)
        self._assert_vectors_equal(self._world_position(c), c_pos)

        # -- x aims at child, rotate is zeroed
        a_pos = om.MVector(*self._world_position(a))
        expected = (om.MVector(*b_pos) - a_pos).normal()
        self._assert_vectors_equal(self._axis(a, 0), expected)
        self._assert_vectors_equal(cmds.getAttr(f"{a.full_name()}.rotate")[0], [0, 0, 0])

        # -- y is up as close to world y as possible: it lies in the plane
        # -- of aim and world up (so z is perpendicular to world up) and
        # -- points the same way as world up.
        self.assertAlmostEqual(self._axis(a, 2) * om.MVector(0, 1, 0), 0.0, places=4)
        self.assertGreater(self._axis(a, 1) * om.MVector(0, 1, 0), 0.0)

    def test_orient_to_child_custom_axes(self):
        a, b, c = self._make_chain()
        b.orient_to_child(aim_axis="-y", up_axis="z", world_up=[0, 0, 1])
        self._assert_vectors_equal(self._axis(b, 1), [0, -1, 0])
        self._assert_vectors_equal(self._axis(b, 2), [0, 0, 1])
        self._assert_vectors_equal(self._world_position(c), [2, 2, 0])

    def test_orient_to_child_keeps_child_joint_rotation_zero(self):
        a, b, c = self._make_chain()
        a.set_joint_orient([0.0, 0.0, 45.0])
        a.orient_to_child()
        self._assert_vectors_equal(cmds.getAttr(f"{b.full_name()}.rotate")[0], [0, 0, 0])

    def test_orient_to_child_with_explicit_child(self):
        a, b, c = self._make_chain()
        a.orient_to_child(child=c)
        expected = om.MVector(2, 2, 0).normal()
        self._assert_vectors_equal(self._axis(a, 0), expected)

    def test_orient_to_child_without_child_raises(self):
        _, _, c = self._make_chain()
        with self.assertRaises(ValueError):
            c.orient_to_child()

    def test_orient_to_child_same_axes_raises(self):
        a, _, _ = self._make_chain()
        with self.assertRaises(ValueError):
            a.orient_to_child(aim_axis="x", up_axis="-x")

    def test_orient_to_world(self):
        a, b, c = self._make_chain()
        b.set_joint_orient([0.0, 0.0, 90.0])
        c_pos = self._world_position(c)
        b.orient_to_world()
        self._assert_vectors_equal(self._axis(b, 0), [1, 0, 0])
        self._assert_vectors_equal(self._axis(b, 1), [0, 1, 0])
        self._assert_vectors_equal(self._world_position(c), c_pos)

    def test_freeze_rotation(self):
        a, b, c = self._make_chain()
        cmds.setAttr(f"{a.full_name()}.rotate", 10, 20, 30)
        cmds.setAttr(f"{a.full_name()}.rotateAxis", 5, 0, 0)
        before = self._world_matrix(a)
        c_pos = self._world_position(c)

        a.freeze_rotation()

        self.assertTrue(self._world_matrix(a).isEquivalent(before, 1e-5))
        self._assert_vectors_equal(cmds.getAttr(f"{a.full_name()}.rotate")[0], [0, 0, 0])
        self._assert_vectors_equal(cmds.getAttr(f"{a.full_name()}.rotateAxis")[0], [0, 0, 0])
        self._assert_vectors_equal(self._world_position(c), c_pos)

    def test_freeze_rotation_respects_rotate_order(self):
        a, _, _ = self._make_chain()
        cmds.setAttr(f"{a.full_name()}.rotateOrder", 4)  # -- xzy
        cmds.setAttr(f"{a.full_name()}.rotate", 30, 60, 90)
        before = self._world_matrix(a)
        a.freeze_rotation()
        self.assertTrue(self._world_matrix(a).isEquivalent(before, 1e-5))


if __name__ == "__main__":
    unittest.main()
