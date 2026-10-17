import unittest

import maya.standalone
import mref
from maya import cmds


class TestConstructionHistory(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_cube_chain(self):
        """
        Builds polyCube -> polyExtrudeFace -> polySmoothFace on a cube
        and returns (transform, shape, cube, extrude, smooth).
        """
        transform, cube = cmds.polyCube(name="box")
        shape = cmds.listRelatives(transform, shapes=True)[0]
        extrude = cmds.polyExtrudeFacet(f"{transform}.f[0]")[0]
        smooth = cmds.polySmooth(transform)[0]
        return transform, shape, cube, extrude, smooth

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_poly_creators_and_modifiers(self):
        transform, _, cube, extrude, smooth = self._make_cube_chain()
        nodes = [
            cube,
            extrude,
            smooth,
            cmds.polyBevel3(f"{transform}.e[0]")[0],
            cmds.polyTriangulate(transform)[0],
            cmds.polyPlane()[1],
            cmds.polyUnite(cmds.polyCube()[0], cmds.polyCube()[0])[1],
        ]
        for node in nodes:
            self.assertIn("ConstructionHistory", mref.get(node).assigned_traits(), node)

    def test_binds_to_nurbs_creators(self):
        circle_a, circle_node = cmds.circle()
        circle_b = cmds.circle()[0]
        cmds.move(0, 2, 0, circle_b)
        nodes = [
            circle_node,
            cmds.sphere()[1],
            cmds.nurbsPlane()[1],
            cmds.loft(circle_a, circle_b)[1],
            cmds.revolve(circle_a)[1],
        ]
        for node in nodes:
            self.assertIn("ConstructionHistory", mref.get(node).assigned_traits(), node)

    def test_does_not_bind_to_unrelated_nodes(self):
        transform, shape, *_ = self._make_cube_chain()
        joint = cmds.createNode("joint")
        skin = cmds.skinCluster(joint, transform)[0]
        for node in (transform, shape, skin, cmds.createNode("multiplyDivide")):
            self.assertNotIn("ConstructionHistory", mref.get(node).assigned_traits(), node)

    # ------------------------------------------------------------------
    # geometry_inputs / geometry_outputs
    # ------------------------------------------------------------------

    def test_geometry_inputs(self):
        _, _, cube, extrude, smooth = self._make_cube_chain()
        self.assertEqual(len(mref.get(cube).geometry_inputs()), 0)

        inputs = mref.get(smooth).geometry_inputs()
        self.assertIsInstance(inputs, mref.ReferenceList)
        self.assertEqual(inputs.names(), [extrude])

    def test_geometry_outputs(self):
        _, shape, cube, extrude, smooth = self._make_cube_chain()
        outputs = mref.get(extrude).geometry_outputs()
        self.assertIsInstance(outputs, mref.ReferenceList)
        self.assertEqual(outputs.names(), [smooth])
        self.assertEqual(mref.get(smooth).geometry_outputs().names(), [shape])

    def test_geometry_inputs_from_curves(self):
        circle_a = cmds.circle(name="ring_a")[0]
        circle_b = cmds.circle(name="ring_b")[0]
        loft = mref.get(cmds.loft(circle_a, circle_b)[1])
        self.assertEqual(sorted(loft.geometry_inputs().names()), ["ring_aShape", "ring_bShape"])

    # ------------------------------------------------------------------
    # output_shapes
    # ------------------------------------------------------------------

    def test_output_shapes(self):
        _, shape, cube, extrude, smooth = self._make_cube_chain()
        for node in (cube, extrude, smooth):
            shapes = mref.get(node).output_shapes()
            self.assertIsInstance(shapes, mref.ReferenceList)
            self.assertEqual(shapes.names(), [shape])

    def test_output_shapes_through_deformers(self):
        transform, cube = cmds.polyCube(name="box")
        shape = cmds.listRelatives(transform, shapes=True)[0]
        joint = cmds.createNode("joint")
        cmds.skinCluster(joint, transform)

        history = mref.get(cube)
        self.assertEqual(history.output_shapes().names(), [shape])

        with_intermediate = history.output_shapes(include_intermediate=True)
        self.assertEqual(len(with_intermediate), 2)
        self.assertIn(shape, with_intermediate.names())

    def test_output_shapes_multiple(self):
        transform_a = cmds.polyCube(name="a")[0]
        transform_b = cmds.polyCube(name="b")[0]
        transform_c, unite = cmds.polyUnite(transform_a, transform_b, constructionHistory=True)
        shape_c = cmds.listRelatives(transform_c, shapes=True)[0]
        self.assertEqual(mref.get(unite).output_shapes().names(), [shape_c])

    # ------------------------------------------------------------------
    # upstream_history / downstream_history
    # ------------------------------------------------------------------

    def test_upstream_history(self):
        _, _, cube, extrude, smooth = self._make_cube_chain()
        upstream = mref.get(smooth).upstream_history()
        self.assertIsInstance(upstream, mref.ReferenceList)
        self.assertEqual(upstream.names(), [extrude, cube])
        self.assertEqual(len(mref.get(cube).upstream_history()), 0)

    def test_downstream_history(self):
        _, _, cube, extrude, smooth = self._make_cube_chain()
        downstream = mref.get(cube).downstream_history()
        self.assertIsInstance(downstream, mref.ReferenceList)
        self.assertEqual(downstream.names(), [extrude, smooth])
        self.assertEqual(len(mref.get(smooth).downstream_history()), 0)

    # ------------------------------------------------------------------
    # is_enabled / set_enabled
    # ------------------------------------------------------------------

    def test_set_enabled(self):
        transform, shape, _, _, smooth = self._make_cube_chain()
        smooth_ref = mref.get(smooth)
        smoothed_count = cmds.polyEvaluate(shape, face=True)

        self.assertTrue(smooth_ref.is_enabled())
        smooth_ref.set_enabled(False)
        self.assertFalse(smooth_ref.is_enabled())
        self.assertLess(cmds.polyEvaluate(shape, face=True), smoothed_count)

        smooth_ref.set_enabled(True)
        self.assertTrue(smooth_ref.is_enabled())
        self.assertEqual(cmds.polyEvaluate(shape, face=True), smoothed_count)

    # ------------------------------------------------------------------
    # bake_history_on_outputs
    # ------------------------------------------------------------------

    def test_bake_history_on_outputs(self):
        transform, shape, cube, extrude, smooth = self._make_cube_chain()
        face_count = cmds.polyEvaluate(shape, face=True)

        baked = mref.get(extrude).bake_history_on_outputs()
        self.assertEqual(baked.names(), [shape])

        for node in (cube, extrude, smooth):
            self.assertFalse(cmds.objExists(node), node)
        self.assertEqual(cmds.polyEvaluate(shape, face=True), face_count)

    def test_bake_history_on_outputs_keeps_deformers(self):
        transform, cube = cmds.polyCube(name="box")
        shape = cmds.listRelatives(transform, shapes=True)[0]
        extrude = cmds.polyExtrudeFacet(f"{transform}.f[0]", localTranslateZ=1)[0]
        face_count = cmds.polyEvaluate(shape, face=True)

        joint = cmds.createNode("joint")
        skin = cmds.skinCluster(joint, transform)[0]

        mref.get(extrude).bake_history_on_outputs()

        self.assertFalse(cmds.objExists(cube))
        self.assertFalse(cmds.objExists(extrude))
        self.assertTrue(cmds.objExists(skin))
        self.assertIn(skin, cmds.listHistory(shape))
        self.assertEqual(cmds.polyEvaluate(shape, face=True), face_count)

        # -- The skin must still drive the mesh
        cmds.move(0, 5, 0, joint)
        self.assertAlmostEqual(cmds.xform(f"{shape}.vtx[0]", query=True, worldSpace=True, translation=True)[1], 4.5, places=3)


if __name__ == "__main__":
    unittest.main()
