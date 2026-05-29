import mref
import unittest
import maya.standalone
from maya import cmds


class TestTransformNode(unittest.TestCase):

    five_up_matrix = [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 5, 0, 1,
    ]

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    # ------------------------------------------------------------------
    # can_bind / matrix
    # ------------------------------------------------------------------

    def test_can_get_matrix(self):
        node = mref.create("transform")
        matrix = node.get_matrix()
        self.assertEqual(len(matrix), 16)

    def test_can_set_matrix(self):
        node = mref.create("transform")
        node.set_matrix(self.five_up_matrix)
        y = cmds.getAttr(f"{node.name()}.translateY")
        self.assertEqual(y, self.five_up_matrix[-3])

    def test_matrix_round_trip_object_space(self):
        node = mref.create("transform")
        node.set_matrix(self.five_up_matrix, space="object")
        self.assertEqual(node.get_matrix(space="object"), self.five_up_matrix)

    def test_matrix_round_trip_world_space(self):
        node = mref.create("transform")
        node.set_matrix(self.five_up_matrix, space="world")
        self.assertEqual(node.get_matrix(space="world"), self.five_up_matrix)

    # ------------------------------------------------------------------
    # space validation
    # ------------------------------------------------------------------

    def test_get_matrix_invalid_space_raises(self):
        node = mref.create("transform")
        with self.assertRaises(ValueError):
            node.get_matrix(space="bogus")

    def test_set_matrix_invalid_space_raises(self):
        node = mref.create("transform")
        with self.assertRaises(ValueError):
            node.set_matrix(self.five_up_matrix, space="bogus")

    def test_position_invalid_space_raises(self):
        node = mref.create("transform")
        with self.assertRaises(ValueError):
            node.get_position(space="bogus")

    # ------------------------------------------------------------------
    # position / rotation / scale convenience
    # ------------------------------------------------------------------

    def test_position_round_trip(self):
        node = mref.create("transform")
        node.set_position([2.0, 4.0, 6.0])

        result = node.get_position()
        for actual, expected in zip(result, [2.0, 4.0, 6.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_position_world_space_respects_parent(self):
        parent = mref.create("transform", name="parent_xform")
        parent.set_position([10.0, 0.0, 0.0], space="world")

        child = mref.create("transform", name="child_xform", parent="parent_xform")
        child.set_position([0.0, 5.0, 0.0], space="object")

        for actual, expected in zip(child.get_position(space="world"), [10.0, 5.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_rotation_round_trip(self):
        node = mref.create("transform")
        node.set_rotation([30.0, 45.0, 90.0])

        result = node.get_rotation()
        for actual, expected in zip(result, [30.0, 45.0, 90.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_scale_round_trip(self):
        node = mref.create("transform")
        node.set_scale([2.0, 3.0, 4.0])

        result = node.get_scale()
        for actual, expected in zip(result, [2.0, 3.0, 4.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    # ------------------------------------------------------------------
    # xform passthrough
    # ------------------------------------------------------------------

    def test_xform_query_returns_list(self):
        node = mref.create("transform")
        result = node.xform(query=True, translation=True, worldSpace=True)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)

    def test_xform_set_returns_none(self):
        node = mref.create("transform")
        result = node.xform(translation=[1.0, 2.0, 3.0], worldSpace=True)
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # match_to
    # ------------------------------------------------------------------

    def test_match_to_snaps_worldspace_position(self):
        a = mref.create("transform", name="a")
        b = mref.create("transform", name="b")
        b.set_position([5.0, 3.0, 1.0], space="world")

        a.match_to(b)

        for av, bv in zip(a.get_position(space="world"), b.get_position(space="world")):
            self.assertAlmostEqual(av, bv, places=4)

    def test_match_to_snaps_worldspace_rotation(self):
        a = mref.create("transform", name="a")
        b = mref.create("transform", name="b")
        b.set_rotation([10.0, 20.0, 30.0], space="world")

        a.match_to(b)

        for av, bv in zip(a.get_rotation(space="world"), b.get_rotation(space="world")):
            self.assertAlmostEqual(av, bv, places=4)

    def test_match_to_object_space(self):
        a = mref.create("transform", name="a")
        b = mref.create("transform", name="b")
        b.set_position([7.0, 8.0, 9.0])

        a.match_to(b, space="object")

        for av, bv in zip(a.get_position(), b.get_position()):
            self.assertAlmostEqual(av, bv, places=4)


if __name__ == "__main__":
    unittest.main()