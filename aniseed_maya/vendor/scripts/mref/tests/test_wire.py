import unittest

import maya.standalone
import mref
from maya import cmds


class TestWire(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_wire(self):
        plane = cmds.polyPlane(name="plane", width=4, height=4)[0]
        curve = cmds.curve(name="curveA", point=[(-2, 0, 0), (-1, 0, 0), (1, 0, 0), (2, 0, 0)])
        wire = cmds.wire(plane, wire=curve, name="wire")[0]
        return mref.get(wire), plane, curve

    def _make_second_curve(self):
        return cmds.curve(name="curveB", point=[(-2, 0, 1), (-1, 0, 1), (1, 0, 1), (2, 0, 1)])

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_wire(self):
        wire_ref, _, _ = self._make_wire()
        traits = wire_ref.assigned_traits()
        self.assertIn("Wire", traits)
        self.assertIn("GeometryFilter", traits)

    def test_does_not_bind_to_other_nodes(self):
        _, plane, curve = self._make_wire()
        cluster = cmds.cluster(plane)[0]
        for node in (plane, curve, cluster):
            self.assertNotIn("Wire", mref.get(node).assigned_traits())

    # ------------------------------------------------------------------
    # wires / base wires / add_wire
    # ------------------------------------------------------------------

    def test_wires(self):
        wire_ref, _, curve = self._make_wire()
        wires = wire_ref.wires()
        self.assertIsInstance(wires, mref.ReferenceList)
        self.assertEqual(len(wires), 1)
        self.assertEqual(wires[0].transform().name(), curve)

    def test_base_wires(self):
        wire_ref, _, _ = self._make_wire()
        base_wires = wire_ref.base_wires()
        self.assertEqual(len(base_wires), 1)
        self.assertNotEqual(base_wires[0], wire_ref.wires()[0])
        self.assertIn("BaseWire", base_wires[0].transform().name())

    def test_add_wire(self):
        wire_ref, _, curve = self._make_wire()
        curve_b = self._make_second_curve()
        wire_ref.add_wire(curve_b)
        self.assertEqual(
            [shape.transform().name() for shape in wire_ref.wires()],
            [curve, curve_b],
        )
        self.assertEqual(len(wire_ref.base_wires()), 2)

    # ------------------------------------------------------------------
    # dropoff distance
    # ------------------------------------------------------------------

    def test_dropoff_distance(self):
        wire_ref, _, _ = self._make_wire()
        self.assertAlmostEqual(wire_ref.dropoff_distance(), 1.0)

    def test_set_dropoff_distance_by_index(self):
        wire_ref, _, _ = self._make_wire()
        wire_ref.set_dropoff_distance(3.0, 0)
        self.assertAlmostEqual(wire_ref.dropoff_distance(0), 3.0)
        self.assertAlmostEqual(cmds.getAttr("wire.dropoffDistance[0]"), 3.0)

    def test_set_dropoff_distance_by_curve(self):
        wire_ref, _, _ = self._make_wire()
        curve_b = self._make_second_curve()
        wire_ref.add_wire(curve_b)
        wire_ref.set_dropoff_distance(5.0, curve_b)
        self.assertAlmostEqual(wire_ref.dropoff_distance(curve_b), 5.0)
        curve_b_shape = cmds.listRelatives(curve_b, shapes=True)[0]
        self.assertAlmostEqual(wire_ref.dropoff_distance(f"{curve_b}|{curve_b_shape}"), 5.0)
        self.assertAlmostEqual(wire_ref.dropoff_distance("curveA"), 1.0)

    def test_set_dropoff_distance_all(self):
        wire_ref, _, _ = self._make_wire()
        wire_ref.add_wire(self._make_second_curve())
        wire_ref.set_dropoff_distance(2.0)
        self.assertAlmostEqual(wire_ref.dropoff_distance(0), 2.0)
        self.assertAlmostEqual(wire_ref.dropoff_distance(1), 2.0)

    def test_dropoff_distance_unknown_curve(self):
        wire_ref, _, _ = self._make_wire()
        other = self._make_second_curve()
        with self.assertRaises(ValueError):
            wire_ref.dropoff_distance(other)

    # ------------------------------------------------------------------
    # wire scale
    # ------------------------------------------------------------------

    def test_wire_scale(self):
        wire_ref, _, _ = self._make_wire()
        self.assertAlmostEqual(wire_ref.wire_scale(), 1.0)
        wire_ref.set_wire_scale(0.5, "curveA")
        self.assertAlmostEqual(wire_ref.wire_scale(0), 0.5)

    def test_set_wire_scale_all(self):
        wire_ref, _, _ = self._make_wire()
        wire_ref.add_wire(self._make_second_curve())
        wire_ref.set_wire_scale(0.0)
        self.assertAlmostEqual(wire_ref.wire_scale(0), 0.0)
        self.assertAlmostEqual(wire_ref.wire_scale(1), 0.0)

    # ------------------------------------------------------------------
    # deformer-wide settings
    # ------------------------------------------------------------------

    def test_wire_rotation(self):
        wire_ref, _, _ = self._make_wire()
        self.assertAlmostEqual(wire_ref.wire_rotation(), 1.0)
        wire_ref.set_wire_rotation(0.25)
        self.assertAlmostEqual(wire_ref.wire_rotation(), 0.25)

    def test_tension(self):
        wire_ref, _, _ = self._make_wire()
        self.assertAlmostEqual(wire_ref.tension(), 1.0)
        wire_ref.set_tension(0.5)
        self.assertAlmostEqual(wire_ref.tension(), 0.5)

    def test_crossing_effect(self):
        wire_ref, _, _ = self._make_wire()
        self.assertAlmostEqual(wire_ref.crossing_effect(), 0.0)
        wire_ref.set_crossing_effect(1.0)
        self.assertAlmostEqual(wire_ref.crossing_effect(), 1.0)

    def test_local_influence(self):
        wire_ref, _, _ = self._make_wire()
        self.assertAlmostEqual(wire_ref.local_influence(), 0.0)
        wire_ref.set_local_influence(0.75)
        self.assertAlmostEqual(wire_ref.local_influence(), 0.75)

    # ------------------------------------------------------------------
    # deformation and GeometryFilter
    # ------------------------------------------------------------------

    def test_wire_deforms_geometry(self):
        wire_ref, plane, curve = self._make_wire()
        before = cmds.pointPosition(f"{plane}.vtx[60]", world=True)
        cmds.setAttr(f"{curve}.translateY", 1)
        after = cmds.pointPosition(f"{plane}.vtx[60]", world=True)
        self.assertGreater(after[1], before[1])

        wire_ref.set_envelope(0.0)
        self.assertAlmostEqual(wire_ref.envelope(), 0.0)
        self.assertAlmostEqual(cmds.pointPosition(f"{plane}.vtx[60]", world=True)[1], before[1])

    def test_geometry_filter_weights(self):
        wire_ref, _, _ = self._make_wire()
        self.assertEqual(wire_ref.output_geometry().names(), ["planeShape"])
        count = len(wire_ref.deformer_weights())
        self.assertEqual(count, cmds.polyEvaluate("plane", vertex=True))
        wire_ref.set_deformer_weights([0.5] * count)
        self.assertEqual(wire_ref.deformer_weights(), [0.5] * count)


if __name__ == "__main__":
    unittest.main()
