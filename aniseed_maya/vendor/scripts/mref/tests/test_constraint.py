import unittest

import maya.standalone
import mref
from maya import cmds


class TestConstraint(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_point_constraint(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        constraint = cmds.pointConstraint(driver, target)[0]
        return mref.get(constraint), driver, target

    # ------------------------------------------------------------------
    # driven / drivers
    # ------------------------------------------------------------------

    def test_driven_returns_constrained_node(self):
        constraint_ref, _, _ = self._make_point_constraint()
        driven = constraint_ref.driven()
        self.assertIsNotNone(driven)
        self.assertEqual(driven.name(), "target")

    def test_drivers_returns_driver_list(self):
        constraint_ref, _, _ = self._make_point_constraint()
        drivers = constraint_ref.drivers()
        self.assertEqual(len(drivers), 1)
        self.assertEqual(drivers[0].name(), "driver")

    def test_drivers_returns_reference_list(self):
        constraint_ref, _, _ = self._make_point_constraint()
        self.assertIsInstance(constraint_ref.drivers(), mref.ReferenceList)

    def test_drivers_excludes_target_parent_matrix(self):
        # -- Regression guard for the useLongNames=False bug where the
        # -- targetParentMatrix filter never matched, leading to the
        # -- parent transform being captured as a driver.
        parent = cmds.createNode("transform", name="parent_xform")
        driver = cmds.createNode("transform", name="driver", parent=parent)
        target = cmds.createNode("transform", name="target")
        constraint = cmds.pointConstraint(driver, target)[0]

        constraint_ref = mref.get(constraint)
        drivers = constraint_ref.drivers()

        driver_names = [d.name() for d in drivers]
        self.assertIn("driver", driver_names)
        self.assertNotIn("parent_xform", driver_names)

    # ------------------------------------------------------------------
    # weight_attributes
    # ------------------------------------------------------------------

    def test_weight_attributes_returns_one_per_driver(self):
        constraint_ref, _, _ = self._make_point_constraint()
        attrs = constraint_ref.weight_attributes()
        self.assertEqual(len(attrs), 1)

    def test_weight_attributes_returns_reference_list(self):
        constraint_ref, _, _ = self._make_point_constraint()
        self.assertIsInstance(
            constraint_ref.weight_attributes(),
            mref.ReferenceList,
        )

    def test_weight_attributes_with_two_drivers(self):
        driver_a = cmds.createNode("transform", name="driver_a")
        driver_b = cmds.createNode("transform", name="driver_b")
        target = cmds.createNode("transform", name="target")
        constraint = cmds.pointConstraint(driver_a, driver_b, target)[0]

        constraint_ref = mref.get(constraint)
        attrs = constraint_ref.weight_attributes()
        self.assertEqual(len(attrs), 2)

    # ------------------------------------------------------------------
    # Binding
    # ------------------------------------------------------------------

    def test_binds_to_constraint(self):
        constraint_ref, _, _ = self._make_point_constraint()
        self.assertIn("Constraint", constraint_ref.assigned_traits())

    def test_does_not_bind_to_transform(self):
        self.assertNotIn("Constraint", mref.create("transform").assigned_traits())

    # ------------------------------------------------------------------
    # Target management
    # ------------------------------------------------------------------

    def test_add_target(self):
        constraint_ref, _, _ = self._make_point_constraint()
        cmds.createNode("transform", name="driver_b")
        weight = constraint_ref.add_target("driver_b", weight=0.25)

        self.assertEqual(constraint_ref.drivers().names(), ["driver", "driver_b"])
        self.assertAlmostEqual(weight.get(), 0.25, places=4)
        self.assertEqual(weight.name(), "driver_bW1")

    def test_add_target_maintain_offset(self):
        constraint_ref, _, _ = self._make_point_constraint()
        cmds.createNode("transform", name="driver_b")
        cmds.setAttr("driver_b.translateX", 4)
        constraint_ref.add_target("driver_b", maintain_offset=True)
        # -- With an offset the target should not have moved
        self.assertAlmostEqual(cmds.getAttr("target.translateX"), 0.0, places=4)

    def test_add_target_keeps_aim_vector(self):
        driver = cmds.createNode("transform", name="driver")
        cmds.createNode("transform", name="driver_b")
        target = cmds.createNode("transform", name="target")
        aim = mref.get(cmds.aimConstraint(driver, target, aimVector=(0, 1, 0))[0])
        aim.add_target("driver_b")
        self.assertEqual(aim.aim_vector(), [0.0, 1.0, 0.0])
        self.assertEqual(len(aim.drivers()), 2)

    def test_add_pole_vector_target(self):
        cmds.createNode("transform", name="pv_a")
        cmds.createNode("transform", name="pv_b")
        cmds.select(clear=True)
        start = cmds.joint(name="start", position=(0, 0, 0))
        cmds.joint(name="mid", position=(0, 5, 1))
        end = cmds.joint(name="end", position=(0, 10, 0))
        handle = cmds.ikHandle(startJoint=start, endEffector=end, solver="ikRPsolver")[0]
        pv = mref.get(cmds.poleVectorConstraint("pv_a", handle)[0])
        pv.add_target("pv_b")
        self.assertEqual(pv.drivers().names(), ["pv_a", "pv_b"])

    def test_remove_target(self):
        driver_a = cmds.createNode("transform", name="driver_a")
        driver_b = cmds.createNode("transform", name="driver_b")
        target = cmds.createNode("transform", name="target")
        constraint_ref = mref.get(cmds.pointConstraint(driver_a, driver_b, target)[0])

        constraint_ref.remove_target("driver_a")
        self.assertEqual(constraint_ref.drivers().names(), ["driver_b"])

    def test_target_weight(self):
        constraint_ref, _, _ = self._make_point_constraint()
        self.assertAlmostEqual(constraint_ref.target_weight("driver"), 1.0, places=4)

    def test_set_target_weight(self):
        driver_a = cmds.createNode("transform", name="driver_a")
        driver_b = cmds.createNode("transform", name="driver_b")
        target = cmds.createNode("transform", name="target")
        constraint_ref = mref.get(cmds.pointConstraint(driver_a, driver_b, target)[0])

        constraint_ref.set_target_weight("driver_b", 0.3)
        self.assertAlmostEqual(constraint_ref.target_weight("driver_b"), 0.3, places=4)
        self.assertAlmostEqual(constraint_ref.target_weight("driver_a"), 1.0, places=4)
        self.assertAlmostEqual(cmds.getAttr(f"{constraint_ref.full_name()}.driver_bW1"), 0.3, places=4)

    def test_target_weight_unknown_driver_raises(self):
        constraint_ref, _, _ = self._make_point_constraint()
        cmds.createNode("transform", name="stranger")
        with self.assertRaises(ValueError):
            constraint_ref.target_weight("stranger")

    # ------------------------------------------------------------------
    # Offsets
    # ------------------------------------------------------------------

    def test_offset_values(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        cmds.setAttr(f"{target}.translateX", 2)
        constraint_ref = mref.get(cmds.pointConstraint(driver, target, maintainOffset=True)[0])
        self.assertEqual(constraint_ref.offset_values(), [2.0, 0.0, 0.0])

        constraint_ref.set_offset_values([0, 3, 0])
        self.assertEqual(constraint_ref.offset_values(), [0.0, 3.0, 0.0])
        self.assertAlmostEqual(cmds.getAttr("target.translateY"), 3.0, places=4)

    def test_offset_attribute_still_resolves(self):
        # -- offset_values is deliberately not named offset, so the
        # -- Maya attribute stays reachable by property syntax.
        constraint_ref, _, _ = self._make_point_constraint()
        self.assertEqual(constraint_ref.offset.name(), "offset")

    def test_offset_values_none_for_parent_constraint(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        constraint_ref = mref.get(cmds.parentConstraint(driver, target)[0])
        self.assertIsNone(constraint_ref.offset_values())
        with self.assertRaises(RuntimeError):
            constraint_ref.set_offset_values([0, 0, 0])

    def test_target_offset(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        cmds.setAttr(f"{target}.translateZ", 5)
        constraint_ref = mref.get(cmds.parentConstraint(driver, target, maintainOffset=True)[0])
        offset = constraint_ref.target_offset("driver")
        self.assertEqual(offset["translate"], [0.0, 0.0, 5.0])
        self.assertEqual(offset["rotate"], [0.0, 0.0, 0.0])

    def test_target_offset_none_for_point_constraint(self):
        constraint_ref, _, _ = self._make_point_constraint()
        self.assertIsNone(constraint_ref.target_offset("driver"))

    # ------------------------------------------------------------------
    # Behaviour settings
    # ------------------------------------------------------------------

    def test_interpolation_type(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        constraint_ref = mref.get(cmds.orientConstraint(driver, target)[0])
        self.assertIn(constraint_ref.interpolation_type(), ["noFlip", "average", "shortest", "longest", "cache"])

        constraint_ref.set_interpolation_type("shortest")
        self.assertEqual(constraint_ref.interpolation_type(), "shortest")
        with self.assertRaises(ValueError):
            constraint_ref.set_interpolation_type("bogus")

    def test_interpolation_type_none_for_point(self):
        constraint_ref, _, _ = self._make_point_constraint()
        self.assertIsNone(constraint_ref.interpolation_type())

    def test_skipped_axes(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        point = mref.get(cmds.pointConstraint(driver, target, skip="y")[0])
        self.assertEqual(point.skipped_axes(), {"translate": ["y"]})

        other = cmds.createNode("transform", name="other")
        parent = mref.get(cmds.parentConstraint(driver, other, skipRotate=["x", "z"])[0])
        self.assertEqual(parent.skipped_axes(), {"translate": [], "rotate": ["x", "z"]})

    def test_rest_position(self):
        constraint_ref, _, _ = self._make_point_constraint()
        rest = constraint_ref.rest_position()
        self.assertIn("enabled", rest)
        self.assertIn("translate", rest)

        constraint_ref.set_rest_position(translate=[1, 2, 3], enabled=True)
        rest = constraint_ref.rest_position()
        self.assertTrue(rest["enabled"])
        self.assertEqual(rest["translate"], [1.0, 2.0, 3.0])

    def test_set_rest_position_rejects_missing_channel(self):
        constraint_ref, _, _ = self._make_point_constraint()
        with self.assertRaises(RuntimeError):
            constraint_ref.set_rest_position(rotate=[0, 0, 0])

    # ------------------------------------------------------------------
    # Aim-style settings
    # ------------------------------------------------------------------

    def _make_aim_constraint(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        return mref.get(cmds.aimConstraint(driver, target)[0])

    def test_aim_and_up_vectors(self):
        aim = self._make_aim_constraint()
        aim.set_aim_vector([0, 0, 1])
        aim.set_up_vector([1, 0, 0])
        self.assertEqual(aim.aim_vector(), [0.0, 0.0, 1.0])
        self.assertEqual(aim.up_vector(), [1.0, 0.0, 0.0])

    def test_aim_vector_none_for_point(self):
        constraint_ref, _, _ = self._make_point_constraint()
        self.assertIsNone(constraint_ref.aim_vector())
        self.assertIsNone(constraint_ref.up_vector())
        self.assertIsNone(constraint_ref.world_up_type())
        self.assertIsNone(constraint_ref.world_up_object())
        with self.assertRaises(RuntimeError):
            constraint_ref.set_aim_vector([1, 0, 0])

    def test_world_up_type(self):
        aim = self._make_aim_constraint()
        self.assertIn(aim.world_up_type(), ["scene", "object", "objectrotation", "vector", "none"])

        up = cmds.createNode("transform", name="up_obj")
        aim.set_world_up_type("object", world_up_object=up)
        self.assertEqual(aim.world_up_type(), "object")
        self.assertEqual(aim.world_up_object().name(), "up_obj")

        aim.set_world_up_type("vector", world_up_vector=[0, 0, 1])
        self.assertEqual(aim.world_up_type(), "vector")
        self.assertEqual(list(cmds.getAttr(f"{aim.full_name()}.worldUpVector")[0]), [0.0, 0.0, 1.0])

    def test_set_world_up_type_rejects_unknown(self):
        with self.assertRaises(ValueError):
            self._make_aim_constraint().set_world_up_type("sideways")

    # ------------------------------------------------------------------
    # bake
    # ------------------------------------------------------------------

    def test_bake(self):
        driver = cmds.createNode("transform", name="driver")
        target = cmds.createNode("transform", name="target")
        cmds.setKeyframe(f"{driver}.translateX", time=1, value=0)
        cmds.setKeyframe(f"{driver}.translateX", time=5, value=10)
        constraint_ref = mref.get(cmds.pointConstraint(driver, target)[0])
        constraint_name = constraint_ref.name()

        constraint_ref.bake(start=1, end=5)

        self.assertFalse(cmds.objExists(constraint_name))
        self.assertTrue(cmds.listConnections("target.translateX", type="animCurve"))
        self.assertEqual(cmds.keyframe("target.translateX", query=True, keyframeCount=True), 5)
        cmds.currentTime(5)
        self.assertAlmostEqual(cmds.getAttr("target.translateX"), 10.0, places=4)

    def test_bake_keep_constraint(self):
        constraint_ref, _, _ = self._make_point_constraint()
        name = constraint_ref.full_name()
        constraint_ref.bake(start=1, end=2, delete_constraint=False)
        self.assertTrue(cmds.objExists(name))


if __name__ == "__main__":
    unittest.main()