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

    def assertVectorAlmostEqual(self, actual, expected, places=4):
        self.assertEqual(len(actual), len(expected))
        for av, ev in zip(actual, expected):
            self.assertAlmostEqual(av, ev, places=places)

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_transform_not_shape(self):
        transform = cmds.polyCube(name="cube")[0]
        self.assertIn("Transform", mref.get(transform).assigned_traits())
        self.assertNotIn("Transform", mref.get(transform).shape().assigned_traits())

    # ------------------------------------------------------------------
    # offset parent matrix
    # ------------------------------------------------------------------

    def test_offset_parent_matrix_round_trip(self):
        node = mref.create("transform")
        identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        self.assertVectorAlmostEqual(node.get_offset_parent_matrix(), identity)

        node.set_offset_parent_matrix(self.five_up_matrix)
        self.assertVectorAlmostEqual(node.get_offset_parent_matrix(), self.five_up_matrix)
        self.assertVectorAlmostEqual(node.get_position(space="world"), [0, 5, 0])
        self.assertVectorAlmostEqual(node.get_position(), [0, 0, 0])

    # ------------------------------------------------------------------
    # pivots
    # ------------------------------------------------------------------

    def test_pivot_round_trip_moves_both_pivots(self):
        node = mref.create("transform")
        node.set_pivot([1.0, 2.0, 3.0])

        self.assertVectorAlmostEqual(node.get_pivot(), [1.0, 2.0, 3.0])
        self.assertVectorAlmostEqual(
            cmds.xform(node.full_name(), query=True, scalePivot=True, objectSpace=True),
            [1.0, 2.0, 3.0],
        )
        self.assertVectorAlmostEqual(node.get_position(), [0.0, 0.0, 0.0])

    def test_pivot_world_space(self):
        node = mref.create("transform")
        node.set_position([10.0, 0.0, 0.0])
        node.set_pivot([10.0, 1.0, 0.0], space="world")

        self.assertVectorAlmostEqual(node.get_pivot(space="world"), [10.0, 1.0, 0.0])
        self.assertVectorAlmostEqual(node.get_pivot(), [0.0, 1.0, 0.0])

    # ------------------------------------------------------------------
    # rotate order
    # ------------------------------------------------------------------

    def test_rotate_order_round_trip(self):
        node = mref.create("transform")
        self.assertEqual(node.get_rotate_order(), "xyz")

        node.set_rotate_order("zxy", preserve=False)
        self.assertEqual(node.get_rotate_order(), "zxy")
        self.assertEqual(cmds.getAttr(f"{node.full_name()}.rotateOrder"), 2)

    def test_set_rotate_order_preserves_orientation(self):
        node = mref.create("transform")
        node.set_rotation([30.0, 45.0, 60.0])
        before = node.get_matrix(space="world")

        node.set_rotate_order("zyx")
        self.assertVectorAlmostEqual(node.get_matrix(space="world"), before)

    # ------------------------------------------------------------------
    # limits
    # ------------------------------------------------------------------

    def test_limits_disabled_by_default(self):
        node = mref.create("transform")
        self.assertEqual(node.get_limits("tx"), [None, None])

    def test_limits_round_trip(self):
        node = mref.create("transform")
        node.set_limits("translateY", 0.0, 10.0)
        self.assertVectorAlmostEqual(node.get_limits("ty"), [0.0, 10.0])

        node.set_limits("ty", minimum=-1.0)
        limits = node.get_limits("ty")
        self.assertAlmostEqual(limits[0], -1.0)
        self.assertIsNone(limits[1])

        node.set_limits("ty")
        self.assertEqual(node.get_limits("ty"), [None, None])

    def test_rotate_limits_are_degrees(self):
        node = mref.create("transform")
        node.set_limits("rz", -45.0, 90.0)
        self.assertVectorAlmostEqual(node.get_limits("rotateZ"), [-45.0, 90.0])

    def test_limits_invalid_channel_raises(self):
        node = mref.create("transform")
        with self.assertRaises(ValueError):
            node.get_limits("visibility")

    # ------------------------------------------------------------------
    # freeze / reset
    # ------------------------------------------------------------------

    def test_freeze_transforms_keeps_geometry_in_place(self):
        transform = cmds.polyCube(name="cube")[0]
        node = mref.get(transform)
        node.set_position([1.0, 2.0, 3.0])
        node.set_scale([2.0, 2.0, 2.0])
        bbox_before = cmds.exactWorldBoundingBox(transform)

        node.freeze_transforms()

        self.assertVectorAlmostEqual(node.get_position(), [0.0, 0.0, 0.0])
        self.assertVectorAlmostEqual(node.get_scale(), [1.0, 1.0, 1.0])
        self.assertVectorAlmostEqual(cmds.exactWorldBoundingBox(transform), bbox_before)

    def test_freeze_transforms_selective_channels(self):
        transform = cmds.polyCube(name="cube")[0]
        node = mref.get(transform)
        node.set_position([1.0, 2.0, 3.0])
        node.set_scale([2.0, 2.0, 2.0])

        node.freeze_transforms(translate=False, rotate=False)

        self.assertVectorAlmostEqual(node.get_position(), [1.0, 2.0, 3.0])
        self.assertVectorAlmostEqual(node.get_scale(), [1.0, 1.0, 1.0])

    def test_reset_transforms(self):
        node = mref.create("transform")
        node.set_position([1.0, 2.0, 3.0])
        node.set_rotation([10.0, 20.0, 30.0])
        node.set_scale([2.0, 3.0, 4.0])

        node.reset_transforms()

        self.assertVectorAlmostEqual(node.get_position(), [0.0, 0.0, 0.0])
        self.assertVectorAlmostEqual(node.get_rotation(), [0.0, 0.0, 0.0])
        self.assertVectorAlmostEqual(node.get_scale(), [1.0, 1.0, 1.0])

    # ------------------------------------------------------------------
    # axis_vector
    # ------------------------------------------------------------------

    def test_axis_vector_follows_rotation(self):
        node = mref.create("transform")
        node.set_rotation([0.0, 0.0, 90.0])

        self.assertVectorAlmostEqual(node.axis_vector("x"), [0.0, 1.0, 0.0])
        self.assertVectorAlmostEqual(node.axis_vector("y"), [-1.0, 0.0, 0.0])
        self.assertVectorAlmostEqual(node.axis_vector("-x"), [0.0, -1.0, 0.0])
        self.assertVectorAlmostEqual(node.axis_vector("z"), [0.0, 0.0, 1.0])

    def test_axis_vector_is_normalised_and_world_space(self):
        parent = mref.create("transform", name="parent_xform")
        parent.set_rotation([0.0, 90.0, 0.0])
        child = mref.create("transform", name="child_xform", parent="parent_xform")
        child.set_scale([5.0, 5.0, 5.0])

        self.assertVectorAlmostEqual(child.axis_vector("x"), [0.0, 0.0, -1.0])
        self.assertVectorAlmostEqual(child.axis_vector("x", space="object"), [1.0, 0.0, 0.0])

    def test_axis_vector_invalid_raises(self):
        with self.assertRaises(ValueError):
            mref.create("transform").axis_vector("w")

    # ------------------------------------------------------------------
    # aim_at
    # ------------------------------------------------------------------

    def test_aim_at_node(self):
        node = mref.create("transform", name="aimer")
        target = mref.create("transform", name="target")
        target.set_position([0.0, 0.0, 10.0], space="world")
        before = set(cmds.ls())

        node.aim_at(target)

        self.assertVectorAlmostEqual(node.axis_vector("x"), [0.0, 0.0, 1.0])
        self.assertVectorAlmostEqual(node.axis_vector("y"), [0.0, 1.0, 0.0])
        self.assertEqual(set(cmds.ls()), before)
        self.assertEqual(node.constraints(), [])

    def test_aim_at_position_with_custom_axes(self):
        node = mref.create("transform", name="aimer")
        node.set_position([1.0, 1.0, 1.0], space="world")
        before = set(cmds.ls())

        node.aim_at(
            [1.0, 6.0, 1.0],
            aim_vector=(0.0, 0.0, 1.0),
            up_vector=(0.0, 1.0, 0.0),
            world_up_vector=(1.0, 0.0, 0.0),
        )

        self.assertVectorAlmostEqual(node.axis_vector("z"), [0.0, 1.0, 0.0])
        self.assertVectorAlmostEqual(node.axis_vector("y"), [1.0, 0.0, 0.0])
        self.assertVectorAlmostEqual(node.get_position(space="world"), [1.0, 1.0, 1.0])
        self.assertEqual(set(cmds.ls()), before)

    def test_aim_at_world_up_object(self):
        node = mref.create("transform", name="aimer")
        target = mref.create("transform", name="target")
        target.set_position([10.0, 0.0, 0.0], space="world")
        up = mref.create("transform", name="up")
        up.set_position([0.0, 0.0, 5.0], space="world")

        node.aim_at(target, world_up_object=up)

        self.assertVectorAlmostEqual(node.axis_vector("x"), [1.0, 0.0, 0.0])
        self.assertVectorAlmostEqual(node.axis_vector("y"), [0.0, 0.0, 1.0])


if __name__ == "__main__":
    unittest.main()