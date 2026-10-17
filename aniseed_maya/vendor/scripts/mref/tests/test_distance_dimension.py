import unittest

import maya.standalone
import mref
from maya import cmds


class TestDistanceDimension(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_dimension(self):
        shape = cmds.distanceDimension(startPoint=(0, 0, 0), endPoint=(3, 4, 0))
        return mref.get(shape)

    def _make_locator(self, name, position):
        locator = cmds.spaceLocator(name=name)[0]
        cmds.setAttr(f"{locator}.translate", *position)
        return locator

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_distance_dimension(self):
        dimension = self._make_dimension()
        self.assertIn("DistanceDimension", dimension.assigned_traits())
        self.assertIn("Shape", dimension.assigned_traits())

    def test_does_not_bind_to_unrelated_nodes(self):
        dimension = self._make_dimension()
        self.assertNotIn("DistanceDimension", dimension.start_locator().assigned_traits())
        self.assertNotIn("DistanceDimension", mref.get(cmds.createNode("distanceBetween")).assigned_traits())

    # ------------------------------------------------------------------
    # distance / positions
    # ------------------------------------------------------------------

    def test_distance(self):
        self.assertAlmostEqual(self._make_dimension().distance(), 5.0, places=4)

    def test_start_and_end_position(self):
        dimension = self._make_dimension()
        self.assertEqual(dimension.start_position(), [0.0, 0.0, 0.0])
        self.assertEqual(dimension.end_position(), [3.0, 4.0, 0.0])

    def test_distance_updates_when_locator_moves(self):
        dimension = self._make_dimension()
        end = dimension.end_locator().parent().full_name()
        cmds.setAttr(f"{end}.translate", 0, 10, 0)
        self.assertAlmostEqual(dimension.distance(), 10.0, places=4)

    # ------------------------------------------------------------------
    # locators
    # ------------------------------------------------------------------

    def test_start_and_end_locator(self):
        dimension = self._make_dimension()
        start = dimension.start_locator()
        end = dimension.end_locator()
        self.assertEqual(start.node_type(), "locator")
        self.assertEqual(end.node_type(), "locator")
        self.assertNotEqual(start, end)

    def test_locators_none_when_unconnected(self):
        dimension = mref.get(cmds.createNode("distanceDimShape"))
        self.assertIsNone(dimension.start_locator())
        self.assertIsNone(dimension.end_locator())

    def test_set_start_locator_with_transform(self):
        dimension = self._make_dimension()
        locator = self._make_locator("newStart", (0, 4, 0))
        dimension.set_start_locator(locator)
        self.assertEqual(dimension.start_locator().parent().name(), "newStart")
        self.assertAlmostEqual(dimension.distance(), 3.0, places=4)

    def test_set_end_locator_with_shape(self):
        dimension = self._make_dimension()
        locator = self._make_locator("newEnd", (0, 0, 2))
        shape = cmds.listRelatives(locator, shapes=True, fullPath=True)[0]
        dimension.set_end_locator(shape)
        self.assertEqual(dimension.end_locator().parent().name(), "newEnd")
        self.assertAlmostEqual(dimension.distance(), 2.0, places=4)

    def test_set_locator_rejects_non_locator(self):
        dimension = self._make_dimension()
        with self.assertRaises(RuntimeError):
            dimension.set_start_locator(cmds.createNode("transform"))


if __name__ == "__main__":
    unittest.main()
