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


if __name__ == "__main__":
    unittest.main()