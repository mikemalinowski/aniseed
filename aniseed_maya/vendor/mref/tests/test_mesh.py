import unittest

import maya.standalone
import mref
from maya import cmds


class TestMesh(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_cube(self):
        transform = cmds.polyCube(name="cube")[0]
        shape = cmds.listRelatives(transform, shapes=True)[0]
        return mref.get(shape), transform

    # ------------------------------------------------------------------
    # counts
    # ------------------------------------------------------------------

    def test_vertex_count(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.vertex_count(), 8)

    def test_polygon_count(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.polygon_count(), 6)

    def test_edge_count(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.edge_count(), 12)

    # ------------------------------------------------------------------
    # vertex positions
    # ------------------------------------------------------------------

    def test_vertex_positions_returns_one_xyz_per_vertex(self):
        ref, _ = self._make_cube()
        positions = ref.vertex_positions()
        self.assertEqual(len(positions), 8)
        for p in positions:
            self.assertEqual(len(p), 3)

    def test_vertex_positions_round_trip(self):
        ref, _ = self._make_cube()
        original = ref.vertex_positions()
        ref.set_vertex_positions(original)
        result = ref.vertex_positions()

        for orig, after in zip(original, result):
            for o, a in zip(orig, after):
                self.assertAlmostEqual(o, a, places=4)

    def test_set_vertex_positions_validates_length(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.set_vertex_positions([[0.0, 0.0, 0.0]] * 5)

    def test_vertex_position_single(self):
        ref, _ = self._make_cube()
        pos = ref.vertex_position(0)
        self.assertEqual(len(pos), 3)

    def test_set_vertex_position_single(self):
        ref, _ = self._make_cube()
        ref.set_vertex_position(0, [1.0, 2.0, 3.0])
        result = ref.vertex_position(0)
        for actual, expected in zip(result, [1.0, 2.0, 3.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    # ------------------------------------------------------------------
    # space validation
    # ------------------------------------------------------------------

    def test_vertex_positions_bogus_space_raises_value_error(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.vertex_positions(space="bogus")

    def test_set_vertex_positions_bogus_space_raises_value_error(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.set_vertex_positions(ref.vertex_positions(), space="bogus")

    # ------------------------------------------------------------------
    # binding / world space
    # ------------------------------------------------------------------

    def test_binds_to_mesh(self):
        ref, _ = self._make_cube()
        self.assertIn("Mesh", ref.assigned_traits())

    def test_does_not_bind_to_unrelated_node(self):
        ref = mref.get(cmds.createNode("transform"))
        self.assertNotIn("Mesh", ref.assigned_traits())

    def test_binds_to_empty_mesh_node(self):
        ref = mref.get(cmds.createNode("mesh"))
        self.assertIsInstance(ref, mref.ReferencedItem)
        self.assertIn("Mesh", ref.assigned_traits())

    def test_vertex_position_world_space(self):
        ref, transform = self._make_cube()
        cmds.setAttr(f"{transform}.translateY", 10)
        local = ref.vertex_position(0)
        world = ref.vertex_position(0, space="world")
        self.assertAlmostEqual(world[1], local[1] + 10, places=4)

    def test_vertex_positions_world_space(self):
        ref, transform = self._make_cube()
        cmds.setAttr(f"{transform}.translateX", 5)
        for local, world in zip(ref.vertex_positions(), ref.vertex_positions(space="world")):
            self.assertAlmostEqual(world[0], local[0] + 5, places=4)

    def test_set_vertex_position_world_space(self):
        ref, transform = self._make_cube()
        cmds.setAttr(f"{transform}.translateX", 5)
        ref.set_vertex_position(0, [5.0, 0.0, 0.0], space="world")
        for actual, expected in zip(ref.vertex_position(0), [0.0, 0.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_world_space_survives_reparent(self):
        ref, transform = self._make_cube()
        parent = cmds.createNode("transform", name="offset")
        cmds.setAttr(f"{parent}.translateZ", 3)
        cmds.parent(transform, parent, relative=True)
        local = ref.vertex_position(0)
        world = ref.vertex_position(0, space="world")
        self.assertAlmostEqual(world[2], local[2] + 3, places=4)

    # ------------------------------------------------------------------
    # normals
    # ------------------------------------------------------------------

    def test_vertex_normals(self):
        ref, _ = self._make_cube()
        normals = ref.vertex_normals()
        self.assertEqual(len(normals), 8)
        # -- Cube corner normals point diagonally away from the centre
        position = ref.vertex_position(0)
        dot = sum(n * p for n, p in zip(normals[0], position))
        self.assertGreater(dot, 0)

    def test_face_normals(self):
        ref, _ = self._make_cube()
        normals = ref.face_normals()
        self.assertEqual(len(normals), 6)
        # -- polyCube face 0 is the front (+Z) face
        for actual, expected in zip(normals[0], [0.0, 0.0, 1.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_face_normals_world_space(self):
        ref, transform = self._make_cube()
        cmds.setAttr(f"{transform}.rotateY", 90)
        for actual, expected in zip(ref.face_normals(space="world")[0], [1.0, 0.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    # ------------------------------------------------------------------
    # topology
    # ------------------------------------------------------------------

    def test_face_vertices_single(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.face_vertices(0), [0, 1, 3, 2])

    def test_face_vertices_all(self):
        ref, _ = self._make_cube()
        faces = ref.face_vertices()
        self.assertEqual(len(faces), 6)
        self.assertEqual(faces[0], ref.face_vertices(0))
        self.assertTrue(all(len(face) == 4 for face in faces))

    def test_edge_vertices(self):
        ref, _ = self._make_cube()
        vertices = ref.edge_vertices(0)
        self.assertEqual(len(vertices), 2)
        self.assertEqual(set(vertices), {0, 1})

    def test_connected_vertices(self):
        ref, _ = self._make_cube()
        self.assertEqual(sorted(ref.connected_vertices(0)), [1, 2, 6])

    def test_border_vertices_closed_mesh(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.border_vertices(), [])

    def test_border_vertices_open_mesh(self):
        transform = cmds.polyPlane(subdivisionsX=2, subdivisionsY=2)[0]
        ref = mref.get(cmds.listRelatives(transform, shapes=True)[0])
        # -- 3x3 grid of vertices: everything except the centre (4)
        self.assertEqual(ref.border_vertices(), [0, 1, 2, 3, 5, 6, 7, 8])

    # ------------------------------------------------------------------
    # uvs
    # ------------------------------------------------------------------

    def test_uv_set_names(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.uv_set_names(), ["map1"])

    def test_current_uv_set(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.current_uv_set(), "map1")

    def test_set_current_uv_set(self):
        ref, transform = self._make_cube()
        cmds.polyUVSet(transform, create=True, uvSet="second")
        ref.set_current_uv_set("second")
        self.assertEqual(ref.current_uv_set(), "second")
        self.assertIn("second", ref.uv_set_names())

    def test_set_current_uv_set_unknown_raises_value_error(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.set_current_uv_set("bogus")

    def test_uv_count(self):
        ref, _ = self._make_cube()
        # -- polyCube's default layout has 14 UVs
        self.assertEqual(ref.uv_count(), 14)
        self.assertEqual(ref.uv_count("map1"), 14)

    def test_uvs(self):
        ref, _ = self._make_cube()
        uvs = ref.uvs()
        self.assertEqual(len(uvs), 14)
        self.assertTrue(all(len(uv) == 2 for uv in uvs))

    def test_uvs_unknown_set_raises_value_error(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.uvs("bogus")

    def test_set_uvs_round_trip(self):
        ref, _ = self._make_cube()
        shifted = [[u + 1.0, v + 2.0] for u, v in ref.uvs()]
        ref.set_uvs(shifted)
        for expected, actual in zip(shifted, ref.uvs()):
            self.assertAlmostEqual(expected[0], actual[0], places=4)
            self.assertAlmostEqual(expected[1], actual[1], places=4)

    def test_set_uvs_validates_length(self):
        ref, _ = self._make_cube()
        with self.assertRaises(ValueError):
            ref.set_uvs([[0.0, 0.0]] * 3)

    def test_uv_at_point(self):
        transform = cmds.polyPlane(subdivisionsX=1, subdivisionsY=1)[0]
        ref = mref.get(cmds.listRelatives(transform, shapes=True)[0])
        u, v, face_id = ref.uv_at_point([0.0, 0.0, 0.0])
        self.assertAlmostEqual(u, 0.5, places=3)
        self.assertAlmostEqual(v, 0.5, places=3)
        self.assertEqual(face_id, 0)

    # ------------------------------------------------------------------
    # spatial queries
    # ------------------------------------------------------------------

    def test_closest_point(self):
        ref, _ = self._make_cube()
        point, normal, face_id = ref.closest_point([0.0, 5.0, 0.0])
        for actual, expected in zip(point, [0.0, 0.5, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)
        for actual, expected in zip(normal, [0.0, 1.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)
        self.assertIn(f".f[{face_id}]", ref.face_component_path(face_id))
        for actual, expected in zip(ref.face_normals()[face_id], [0.0, 1.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_closest_point_world_space(self):
        ref, transform = self._make_cube()
        cmds.setAttr(f"{transform}.translateY", 10)
        point, _, _ = ref.closest_point([0.0, 20.0, 0.0], space="world")
        self.assertAlmostEqual(point[1], 10.5, places=4)

    def test_ray_intersection_hit(self):
        ref, transform = self._make_cube()
        cmds.setAttr(f"{transform}.translateY", 10)
        hit = ref.ray_intersection([0.0, 20.0, 0.0], [0.0, -1.0, 0.0])
        self.assertIsNotNone(hit)
        point, face_id = hit
        self.assertAlmostEqual(point[1], 10.5, places=4)
        self.assertGreaterEqual(face_id, 0)

    def test_ray_intersection_miss(self):
        ref, _ = self._make_cube()
        self.assertIsNone(ref.ray_intersection([0.0, 20.0, 0.0], [0.0, 1.0, 0.0]))

    def test_ray_intersection_both_directions(self):
        ref, _ = self._make_cube()
        hit = ref.ray_intersection([0.0, 20.0, 0.0], [0.0, 1.0, 0.0], both_directions=True)
        self.assertIsNotNone(hit)

    # ------------------------------------------------------------------
    # shading
    # ------------------------------------------------------------------

    def test_shading_engines_default(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.shading_engines().names(), ["initialShadingGroup"])

    def test_shading_engines_per_face(self):
        ref, transform = self._make_cube()
        shader = cmds.shadingNode("lambert", asShader=True)
        engine = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="redSG")
        cmds.connectAttr(f"{shader}.outColor", f"{engine}.surfaceShader")
        cmds.sets(f"{transform}.f[0]", edit=True, forceElement=engine)
        names = ref.shading_engines().names()
        self.assertIn("redSG", names)
        self.assertIn("initialShadingGroup", names)

    # ------------------------------------------------------------------
    # skin discovery
    # ------------------------------------------------------------------

    def test_skin_returns_none_when_no_skin_bound(self):
        ref, _ = self._make_cube()
        self.assertIsNone(ref.skin())

    def test_skin_returns_referenceditem_when_skin_bound(self):
        ref, transform = self._make_cube()
        joint = cmds.createNode("joint", name="bone")
        cmds.skinCluster(joint, transform)
        self.assertIsInstance(ref.skin(), mref.ReferencedItem)

    # ------------------------------------------------------------------
    # skinnable-shape protocol
    # ------------------------------------------------------------------

    def test_component_count_equals_vertex_count(self):
        ref, _ = self._make_cube()
        self.assertEqual(ref.component_count(), ref.vertex_count())

    def test_component_path_uses_vtx_indexing(self):
        ref, _ = self._make_cube()
        path = ref.component_path(0)
        self.assertIn(".vtx[0]", path)

    def test_face_component_path(self):
        ref, _ = self._make_cube()
        path = ref.face_component_path(2)
        self.assertTrue(path.endswith(".f[2]"))
        self.assertTrue(cmds.objExists(path))

    def test_edge_component_path(self):
        ref, _ = self._make_cube()
        path = ref.edge_component_path(3)
        self.assertTrue(path.endswith(".e[3]"))
        self.assertTrue(cmds.objExists(path))


if __name__ == "__main__":
    unittest.main()