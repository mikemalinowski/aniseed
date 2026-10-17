import unittest

import maya.standalone
import mref
from maya import cmds


class TestLattice(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_lattice(self, divisions=(2, 3, 4)):
        cube = cmds.polyCube(name="cube")[0]
        ffd, lattice, base = cmds.lattice(cube, divisions=divisions, name="ffd")
        return mref.get(ffd), cube, lattice, base

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_ffd(self):
        ffd_ref, _, _, _ = self._make_lattice()
        traits = ffd_ref.assigned_traits()
        self.assertIn("Lattice", traits)
        self.assertIn("GeometryFilter", traits)

    def test_does_not_bind_to_other_nodes(self):
        _, cube, lattice, base = self._make_lattice()
        lattice_shape = cmds.listRelatives(lattice, shapes=True)[0]
        for node in (cube, lattice, base, lattice_shape):
            self.assertNotIn("Lattice", mref.get(node).assigned_traits())

    # ------------------------------------------------------------------
    # lattice / base_lattice
    # ------------------------------------------------------------------

    def test_lattice(self):
        ffd_ref, _, lattice, _ = self._make_lattice()
        result = ffd_ref.lattice()
        self.assertEqual(result.name(), cmds.listRelatives(lattice, shapes=True)[0])
        self.assertEqual(result.transform().name(), lattice)

    def test_base_lattice(self):
        ffd_ref, _, _, base = self._make_lattice()
        self.assertEqual(ffd_ref.base_lattice().name(), cmds.listRelatives(base, shapes=True)[0])

    # ------------------------------------------------------------------
    # divisions
    # ------------------------------------------------------------------

    def test_divisions(self):
        ffd_ref, _, _, _ = self._make_lattice()
        self.assertEqual(ffd_ref.divisions(), (2, 3, 4))

    def test_set_divisions(self):
        ffd_ref, _, lattice, _ = self._make_lattice()
        ffd_ref.set_divisions(5, 2, 3)
        self.assertEqual(ffd_ref.divisions(), (5, 2, 3))
        self.assertEqual(cmds.getAttr(f"{lattice}.sDivisions"), 5)

    # ------------------------------------------------------------------
    # local mode
    # ------------------------------------------------------------------

    def test_local(self):
        ffd_ref, _, _, _ = self._make_lattice()
        self.assertFalse(ffd_ref.is_local())
        ffd_ref.set_local(True)
        self.assertTrue(ffd_ref.is_local())

    def test_local_influence(self):
        ffd_ref, _, _, _ = self._make_lattice()
        self.assertEqual(ffd_ref.local_influence(), (2, 2, 2))
        ffd_ref.set_local_influence(3, 4, 5)
        self.assertEqual(ffd_ref.local_influence(), (3, 4, 5))

    # ------------------------------------------------------------------
    # outside lattice
    # ------------------------------------------------------------------

    def test_outside_lattice(self):
        ffd_ref, _, _, _ = self._make_lattice()
        self.assertEqual(ffd_ref.outside_lattice(), "inside")
        ffd_ref.set_outside_lattice("all")
        self.assertEqual(ffd_ref.outside_lattice(), "all")

    def test_set_outside_lattice_with_falloff(self):
        ffd_ref, _, _, _ = self._make_lattice()
        ffd_ref.set_outside_lattice("falloff", falloff_distance=2.5)
        self.assertEqual(ffd_ref.outside_lattice(), "falloff")
        self.assertAlmostEqual(ffd_ref.outside_falloff_distance(), 2.5)

    def test_set_outside_lattice_invalid(self):
        ffd_ref, _, _, _ = self._make_lattice()
        with self.assertRaises(ValueError):
            ffd_ref.set_outside_lattice("nowhere")

    def test_outside_falloff_distance(self):
        ffd_ref, _, _, _ = self._make_lattice()
        self.assertAlmostEqual(ffd_ref.outside_falloff_distance(), cmds.getAttr("ffd.outsideFalloffDist"))

    # ------------------------------------------------------------------
    # GeometryFilter is also bound
    # ------------------------------------------------------------------

    def test_geometry_filter_envelope_and_weights(self):
        ffd_ref, _, _, _ = self._make_lattice()
        ffd_ref.set_envelope(0.5)
        self.assertAlmostEqual(ffd_ref.envelope(), 0.5)
        self.assertEqual(ffd_ref.output_geometry().names(), ["cubeShape"])
        self.assertEqual(ffd_ref.deformer_weights(), [1.0] * 8)


class TestLatticeShape(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_lattice_shape(self, divisions=(2, 3, 4)):
        cube = cmds.polyCube(name="cube")[0]
        ffd, lattice, _ = cmds.lattice(cube, divisions=divisions, name="ffd")
        shape = cmds.listRelatives(lattice, shapes=True)[0]
        return mref.get(shape), ffd, lattice

    def _disconnect_ffd(self, shape_ref, ffd):
        # -- Deleting the ffd also deletes the lattice, so break the
        # -- connection instead to get a lattice which drives nothing
        cmds.disconnectAttr(
            f"{shape_ref.full_name()}.latticeOutput",
            f"{ffd}.deformedLatticePoints",
        )

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_lattice_shape(self):
        shape_ref, _, _ = self._make_lattice_shape()
        traits = shape_ref.assigned_traits()
        self.assertIn("LatticeShape", traits)
        self.assertIn("Shape", traits)

    def test_does_not_bind_to_other_nodes(self):
        _, ffd, lattice = self._make_lattice_shape()
        base_shape = cmds.listRelatives("ffdBase", shapes=True)[0]
        for node in (ffd, lattice, base_shape, "cubeShape"):
            self.assertNotIn("LatticeShape", mref.get(node).assigned_traits())

    # ------------------------------------------------------------------
    # divisions
    # ------------------------------------------------------------------

    def test_divisions(self):
        shape_ref, _, _ = self._make_lattice_shape()
        self.assertEqual(shape_ref.divisions(), (2, 3, 4))

    def test_set_divisions_updates_ffd(self):
        shape_ref, ffd, _ = self._make_lattice_shape()
        shape_ref.set_divisions(3, 3, 3)
        self.assertEqual(shape_ref.divisions(), (3, 3, 3))
        self.assertEqual(cmds.lattice(ffd, query=True, divisions=True), [3, 3, 3])
        self.assertEqual(len(shape_ref.point_positions()), 27)

    def test_set_divisions_without_ffd(self):
        shape_ref, ffd, _ = self._make_lattice_shape()
        self._disconnect_ffd(shape_ref, ffd)
        shape_ref.set_divisions(4, 2, 2)
        self.assertEqual(shape_ref.divisions(), (4, 2, 2))

    # ------------------------------------------------------------------
    # point counts / indices
    # ------------------------------------------------------------------

    def test_point_count(self):
        shape_ref, _, _ = self._make_lattice_shape()
        self.assertEqual(shape_ref.point_count(), 24)

    def test_point_index(self):
        shape_ref, _, _ = self._make_lattice_shape()
        self.assertEqual(shape_ref.point_index(0, 0, 0), 0)
        self.assertEqual(shape_ref.point_index(1, 0, 0), 1)
        self.assertEqual(shape_ref.point_index(0, 1, 0), 2)
        self.assertEqual(shape_ref.point_index(1, 2, 3), 1 + 2 * 2 + 3 * 6)

    def test_point_index_out_of_range(self):
        shape_ref, _, _ = self._make_lattice_shape()
        with self.assertRaises(IndexError):
            shape_ref.point_index(2, 0, 0)

    def test_point_index_matches_component(self):
        shape_ref, _, _ = self._make_lattice_shape()
        index = shape_ref.point_index(1, 2, 3)
        expected = cmds.pointPosition(f"{shape_ref.full_name()}.pt[1][2][3]", local=True)
        for a, b in zip(shape_ref.point_position(index), expected):
            self.assertAlmostEqual(a, b)

    # ------------------------------------------------------------------
    # point positions
    # ------------------------------------------------------------------

    def test_point_positions(self):
        shape_ref, _, _ = self._make_lattice_shape()
        positions = shape_ref.point_positions()
        self.assertEqual(len(positions), 24)
        self.assertEqual([round(v, 4) for v in positions[0]], [-0.5, -0.5, -0.5])
        self.assertEqual([round(v, 4) for v in positions[-1]], [0.5, 0.5, 0.5])

    def test_point_positions_world_space(self):
        shape_ref, _, lattice = self._make_lattice_shape()
        cmds.setAttr(f"{lattice}.translateX", 5)
        self.assertAlmostEqual(shape_ref.point_positions("world")[0][0], 4.5)
        self.assertAlmostEqual(shape_ref.point_positions("object")[0][0], -0.5)

    def test_point_positions_invalid_space(self):
        shape_ref, _, _ = self._make_lattice_shape()
        with self.assertRaises(ValueError):
            shape_ref.point_positions("nowhere")

    def test_set_point_positions(self):
        shape_ref, _, _ = self._make_lattice_shape()
        positions = [[p[0] * 2, p[1] * 2, p[2] * 2] for p in shape_ref.point_positions()]
        shape_ref.set_point_positions(positions)
        for actual, expected in zip(shape_ref.point_positions(), positions):
            for a, b in zip(actual, expected):
                self.assertAlmostEqual(a, b)

    def test_set_point_positions_wrong_length(self):
        shape_ref, _, _ = self._make_lattice_shape()
        with self.assertRaises(ValueError):
            shape_ref.set_point_positions([[0, 0, 0]])

    def test_set_point_positions_deforms_geometry(self):
        shape_ref, _, _ = self._make_lattice_shape()
        before = cmds.pointPosition("cube.vtx[0]", world=True)
        positions = [[p[0] * 2, p[1] * 2, p[2] * 2] for p in shape_ref.point_positions()]
        shape_ref.set_point_positions(positions)
        after = cmds.pointPosition("cube.vtx[0]", world=True)
        self.assertAlmostEqual(after[0], before[0] * 2)

    def test_point_position(self):
        shape_ref, _, _ = self._make_lattice_shape()
        self.assertEqual([round(v, 4) for v in shape_ref.point_position(1)], [0.5, -0.5, -0.5])

    def test_set_point_position(self):
        shape_ref, _, _ = self._make_lattice_shape()
        shape_ref.set_point_position(3, [1.0, 2.0, 3.0])
        self.assertEqual([round(v, 4) for v in shape_ref.point_position(3)], [1.0, 2.0, 3.0])
        # -- Other points are untouched
        self.assertEqual([round(v, 4) for v in shape_ref.point_position(0)], [-0.5, -0.5, -0.5])

    def test_set_point_position_world_space(self):
        shape_ref, _, lattice = self._make_lattice_shape()
        cmds.setAttr(f"{lattice}.translateX", 5)
        shape_ref.set_point_position(0, [5.0, 0.0, 0.0], space="world")
        self.assertEqual([round(v, 4) for v in shape_ref.point_position(0)], [0.0, 0.0, 0.0])

    # ------------------------------------------------------------------
    # ffd_deformers
    # ------------------------------------------------------------------

    def test_ffd_deformers(self):
        shape_ref, ffd, _ = self._make_lattice_shape()
        result = shape_ref.ffd_deformers()
        self.assertIsInstance(result, mref.ReferenceList)
        self.assertEqual(result.names(), [ffd])

    def test_ffd_deformers_empty(self):
        shape_ref, ffd, _ = self._make_lattice_shape()
        self._disconnect_ffd(shape_ref, ffd)
        self.assertEqual(shape_ref.ffd_deformers(), [])

    # ------------------------------------------------------------------
    # skinnable-shape protocol
    # ------------------------------------------------------------------

    def test_component_count(self):
        shape_ref, _, _ = self._make_lattice_shape()
        self.assertEqual(shape_ref.component_count(), 24)

    def test_component_path(self):
        shape_ref, _, _ = self._make_lattice_shape()
        index = shape_ref.point_index(1, 2, 3)
        self.assertEqual(
            shape_ref.component_path(index),
            f"{shape_ref.full_name()}.pt[1][2][3]",
        )

    def test_cluster_weights_on_lattice(self):
        shape_ref, _, _ = self._make_lattice_shape()
        cluster = mref.get(cmds.cluster(shape_ref.full_name())[0])
        self.assertEqual(cluster.deformer_weights(), [1.0] * 24)
        weights = [i / 23.0 for i in range(24)]
        cluster.set_deformer_weights(weights)
        for a, b in zip(cluster.deformer_weights(), weights):
            self.assertAlmostEqual(a, b, places=5)


if __name__ == "__main__":
    unittest.main()
