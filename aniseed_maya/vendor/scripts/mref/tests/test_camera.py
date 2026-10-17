import unittest

import maya.standalone
import mref
from maya import cmds


class TestCamera(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_camera(self):
        transform, shape = cmds.camera()
        return mref.get(shape), transform

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_camera_shape(self):
        camera, _ = self._make_camera()
        self.assertIn("Camera", camera.assigned_traits())
        self.assertIn("Shape", camera.assigned_traits())

    def test_does_not_bind_to_mesh(self):
        mesh = cmds.polyCube()[0]
        shape = cmds.listRelatives(mesh, shapes=True)[0]
        self.assertNotIn("Camera", mref.get(shape).assigned_traits())

    def test_does_not_bind_to_camera_transform(self):
        _, transform = self._make_camera()
        self.assertNotIn("Camera", mref.get(transform).assigned_traits())

    # ------------------------------------------------------------------
    # lens
    # ------------------------------------------------------------------

    def test_focal_length_round_trip(self):
        camera, _ = self._make_camera()
        camera.set_focal_length(50.0)
        self.assertAlmostEqual(camera.focal_length(), 50.0)

    def test_film_aperture_round_trip(self):
        camera, _ = self._make_camera()
        camera.set_film_aperture(1.5, 0.75)
        horizontal, vertical = camera.film_aperture()
        self.assertAlmostEqual(horizontal, 1.5)
        self.assertAlmostEqual(vertical, 0.75)

    def test_field_of_view_narrows_with_focal_length(self):
        camera, _ = self._make_camera()
        camera.set_focal_length(35.0)
        wide = camera.field_of_view()
        camera.set_focal_length(85.0)
        narrow = camera.field_of_view()
        self.assertEqual(len(wide), 2)
        self.assertGreater(wide[0], narrow[0])
        self.assertGreater(wide[1], narrow[1])

    def test_field_of_view_is_in_degrees(self):
        camera, _ = self._make_camera()
        # -- 35mm lens on the default 36x24mm-ish back is ~54 degrees
        self.assertGreater(camera.field_of_view()[0], 10.0)
        self.assertLess(camera.field_of_view()[0], 120.0)

    # ------------------------------------------------------------------
    # clipping / orthographic
    # ------------------------------------------------------------------

    def test_clip_planes_round_trip(self):
        camera, _ = self._make_camera()
        camera.set_clip_planes(0.5, 5000.0)
        near, far = camera.clip_planes()
        self.assertAlmostEqual(near, 0.5)
        self.assertAlmostEqual(far, 5000.0)

    def test_set_clip_planes_partial(self):
        camera, _ = self._make_camera()
        camera.set_clip_planes(near=0.5, far=5000.0)
        camera.set_clip_planes(far=200.0)
        near, far = camera.clip_planes()
        self.assertAlmostEqual(near, 0.5)
        self.assertAlmostEqual(far, 200.0)

    def test_orthographic_toggle(self):
        camera, _ = self._make_camera()
        self.assertFalse(camera.is_orthographic())
        camera.set_orthographic(True)
        self.assertTrue(camera.is_orthographic())
        camera.set_orthographic(False)
        self.assertFalse(camera.is_orthographic())

    def test_set_orthographic_with_width(self):
        camera, _ = self._make_camera()
        camera.set_orthographic(True, width=42.0)
        self.assertTrue(camera.is_orthographic())
        self.assertAlmostEqual(camera.ortho_width(), 42.0)

    def test_ortho_width_round_trip(self):
        camera, _ = self._make_camera()
        camera.set_ortho_width(12.5)
        self.assertAlmostEqual(camera.ortho_width(), 12.5)

    # ------------------------------------------------------------------
    # view vectors
    # ------------------------------------------------------------------

    def test_eye_point_is_world_space(self):
        camera, transform = self._make_camera()
        cmds.xform(transform, worldSpace=True, translation=(1, 2, 3))
        for actual, expected in zip(camera.eye_point(), [1, 2, 3]):
            self.assertAlmostEqual(actual, expected)

    def test_eye_point_follows_parent(self):
        camera, transform = self._make_camera()
        parent = cmds.createNode("transform", name="cam_parent")
        cmds.parent(transform, parent)
        cmds.xform(parent, worldSpace=True, translation=(0, 10, 0))
        self.assertAlmostEqual(camera.eye_point()[1], 10.0)

    def test_default_view_and_up_direction(self):
        camera, _ = self._make_camera()
        for actual, expected in zip(camera.view_direction(), [0, 0, -1]):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(camera.up_direction(), [0, 1, 0]):
            self.assertAlmostEqual(actual, expected)

    def test_view_direction_is_world_space(self):
        camera, transform = self._make_camera()
        cmds.xform(transform, worldSpace=True, rotation=(0, 90, 0))
        for actual, expected in zip(camera.view_direction(), [-1, 0, 0]):
            self.assertAlmostEqual(actual, expected, places=5)

    def test_look_at_point(self):
        camera, _ = self._make_camera()
        camera.look_at([10, 0, 0])
        for actual, expected in zip(camera.view_direction(), [1, 0, 0]):
            self.assertAlmostEqual(actual, expected, places=5)

    def test_look_at_node(self):
        camera, transform = self._make_camera()
        cmds.xform(transform, worldSpace=True, translation=(0, 0, 10))
        target = cmds.createNode("transform", name="target")
        cmds.xform(target, worldSpace=True, translation=(0, 10, 10))
        camera.look_at(mref.get(target))
        for actual, expected in zip(camera.view_direction(), [0, 1, 0]):
            self.assertAlmostEqual(actual, expected, places=4)


if __name__ == "__main__":
    unittest.main()
