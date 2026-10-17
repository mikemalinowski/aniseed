import unittest

import maya.standalone
import mref
from maya import cmds


DEFORMER_TYPES = ["bend", "twist", "flare", "sine", "squash", "wave"]


class TestNonLinear(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_non_linear(self, deformer_type="bend"):
        sphere = cmds.polySphere(name="sphere")[0]
        deformer, handle = cmds.nonLinear(sphere, type=deformer_type)
        return mref.get(deformer), sphere, handle

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_every_type(self):
        for deformer_type in DEFORMER_TYPES:
            deformer_ref, _, _ = self._make_non_linear(deformer_type)
            traits = deformer_ref.assigned_traits()
            self.assertIn("NonLinear", traits, deformer_type)
            self.assertIn("GeometryFilter", traits, deformer_type)

    def test_does_not_bind_to_other_nodes(self):
        _, sphere, handle = self._make_non_linear()
        handle_shape = cmds.listRelatives(handle, shapes=True)[0]
        cluster = cmds.cluster(sphere)[0]
        for node in (sphere, handle, handle_shape, cluster):
            self.assertNotIn("NonLinear", mref.get(node).assigned_traits())

    # ------------------------------------------------------------------
    # handle / handle_shape
    # ------------------------------------------------------------------

    def test_handle(self):
        deformer_ref, _, handle = self._make_non_linear()
        self.assertEqual(deformer_ref.handle().name(), handle)

    def test_handle_shape(self):
        deformer_ref, _, handle = self._make_non_linear()
        handle_shape = cmds.listRelatives(handle, shapes=True)[0]
        self.assertEqual(deformer_ref.handle_shape().name(), handle_shape)

    # ------------------------------------------------------------------
    # deformer_type
    # ------------------------------------------------------------------

    def test_deformer_type(self):
        for deformer_type in DEFORMER_TYPES:
            deformer_ref, _, _ = self._make_non_linear(deformer_type)
            self.assertEqual(deformer_ref.deformer_type(), deformer_type)

    def test_deformer_type_without_handle_shape(self):
        for deformer_type in DEFORMER_TYPES:
            deformer_ref, _, handle = self._make_non_linear(deformer_type)
            cmds.delete(cmds.listRelatives(handle, shapes=True))
            self.assertIsNone(deformer_ref.handle_shape())
            self.assertEqual(deformer_ref.deformer_type(), deformer_type)

    # ------------------------------------------------------------------
    # parameters
    # ------------------------------------------------------------------

    def test_parameters(self):
        deformer_ref, _, _ = self._make_non_linear("bend")
        self.assertEqual(
            deformer_ref.parameters(),
            {"curvature": 0.0, "lowBound": -1.0, "highBound": 1.0},
        )

    def test_parameters_every_type(self):
        for deformer_type in DEFORMER_TYPES:
            deformer_ref, _, _ = self._make_non_linear(deformer_type)
            parameters = deformer_ref.parameters()
            self.assertTrue(parameters, deformer_type)
            for name, value in parameters.items():
                self.assertEqual(value, cmds.getAttr(f"{deformer_ref.full_name()}.{name}"))

    def test_parameter(self):
        deformer_ref, _, _ = self._make_non_linear("sine")
        self.assertAlmostEqual(deformer_ref.parameter("wavelength"), cmds.getAttr(f"{deformer_ref.full_name()}.wavelength"))

    def test_set_parameter_updates_handle_shape(self):
        deformer_ref, _, handle = self._make_non_linear("sine")
        handle_shape = cmds.listRelatives(handle, shapes=True)[0]
        deformer_ref.set_parameter("amplitude", 0.3)
        self.assertAlmostEqual(deformer_ref.parameter("amplitude"), 0.3)
        self.assertAlmostEqual(cmds.getAttr(f"{handle_shape}.amplitude"), 0.3)

    def test_parameter_invalid_for_type(self):
        deformer_ref, _, _ = self._make_non_linear("bend")
        with self.assertRaises(ValueError):
            deformer_ref.parameter("amplitude")
        with self.assertRaises(ValueError):
            deformer_ref.set_parameter("startAngle", 10)

    # ------------------------------------------------------------------
    # bounds / curvature / angles
    # ------------------------------------------------------------------

    def test_bounds(self):
        deformer_ref, _, _ = self._make_non_linear("twist")
        self.assertEqual(deformer_ref.bounds(), (-1.0, 1.0))
        deformer_ref.set_bounds(-0.5, 2.0)
        self.assertEqual(deformer_ref.bounds(), (-0.5, 2.0))

    def test_bounds_not_on_wave(self):
        deformer_ref, _, _ = self._make_non_linear("wave")
        with self.assertRaises(ValueError):
            deformer_ref.bounds()

    def test_curvature(self):
        deformer_ref, sphere, _ = self._make_non_linear("bend")
        before = cmds.pointPosition(f"{sphere}.vtx[0]", world=True)
        self.assertAlmostEqual(deformer_ref.curvature(), 0.0)
        deformer_ref.set_curvature(90.0)
        self.assertAlmostEqual(deformer_ref.curvature(), 90.0)
        after = cmds.pointPosition(f"{sphere}.vtx[0]", world=True)
        self.assertNotAlmostEqual(before[0], after[0])

    def test_curvature_not_on_twist(self):
        deformer_ref, _, _ = self._make_non_linear("twist")
        with self.assertRaises(ValueError):
            deformer_ref.curvature()

    def test_angles(self):
        deformer_ref, _, _ = self._make_non_linear("twist")
        self.assertEqual(deformer_ref.angles(), (0.0, 0.0))
        deformer_ref.set_angles(10.0, 45.0)
        start, end = deformer_ref.angles()
        self.assertAlmostEqual(start, 10.0)
        self.assertAlmostEqual(end, 45.0)

    # ------------------------------------------------------------------
    # GeometryFilter is also bound
    # ------------------------------------------------------------------

    def test_geometry_filter(self):
        deformer_ref, _, _ = self._make_non_linear("squash")
        deformer_ref.set_envelope(0.5)
        self.assertAlmostEqual(deformer_ref.envelope(), 0.5)
        self.assertEqual(deformer_ref.output_geometry().names(), ["sphereShape"])
        count = cmds.polyEvaluate("sphere", vertex=True)
        self.assertEqual(deformer_ref.deformer_weights(), [1.0] * count)
        deformer_ref.set_deformer_weights([0.25] * count)
        self.assertEqual(deformer_ref.deformer_weights(), [0.25] * count)


if __name__ == "__main__":
    unittest.main()
