import unittest

import maya.standalone
import mref
from maya import cmds


class TestSkinCluster(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_skin(self):
        mesh_transform = cmds.polyCube(name="cube")[0]
        joint_a = cmds.createNode("joint", name="bone_a")
        joint_b = cmds.createNode("joint", name="bone_b")
        skin = cmds.skinCluster(joint_a, joint_b, mesh_transform)[0]
        return mref.get(skin), mesh_transform, joint_a, joint_b

    # ------------------------------------------------------------------
    # influences
    # ------------------------------------------------------------------

    def test_influences_returns_joints(self):
        skin_ref, _, _, _ = self._make_skin()
        influences = skin_ref.influences()
        self.assertEqual(len(influences), 2)
        names = sorted(inf.name() for inf in influences)
        self.assertEqual(names, ["bone_a", "bone_b"])

    # ------------------------------------------------------------------
    # shape / shapes
    # ------------------------------------------------------------------

    def test_shape_returns_first_geometry(self):
        skin_ref, _, _, _ = self._make_skin()
        self.assertIsNotNone(skin_ref.shape())

    def test_shapes_returns_list_with_skinned_mesh(self):
        skin_ref, _, _, _ = self._make_skin()
        self.assertEqual(len(skin_ref.shapes()), 1)

    # ------------------------------------------------------------------
    # weights — shape and round-trip
    # ------------------------------------------------------------------

    def test_weights_returns_expected_dict_shape(self):
        skin_ref, _, _, _ = self._make_skin()
        data = skin_ref.weights()

        self.assertIn("influences", data)
        self.assertIn("weights", data)
        self.assertIn("max_influences", data)

        self.assertEqual(len(data["influences"]), 2)
        # Cube has 8 vertices, one weight per vertex per influence
        self.assertEqual(len(data["weights"][0]), 8)
        self.assertEqual(len(data["weights"][1]), 8)

    def test_weights_round_trip(self):
        skin_ref, _, _, _ = self._make_skin()
        original = skin_ref.weights()
        skin_ref.set_weights(original)
        after = skin_ref.weights()

        self.assertEqual(original["influences"], after["influences"])
        for inf_idx in range(len(original["weights"])):
            for v_idx in range(len(original["weights"][inf_idx])):
                self.assertAlmostEqual(
                    original["weights"][inf_idx][v_idx],
                    after["weights"][inf_idx][v_idx],
                    places=4,
                )

    def test_weights_component_major_layout(self):
        # -- Regression guard for the component-major slicing fix.
        # -- With weights 100% to bone_a, the per-influence lists must
        # -- be all-1 for bone_a and all-0 for bone_b. The original
        # -- influence-major slicing produced interleaved [0,1,0,1,...]
        # -- lists for both.
        skin_ref, mesh, joint_a, joint_b = self._make_skin()

        cmds.skinPercent(
            skin_ref.full_name(),
            f"{mesh}.vtx[*]",
            transformValue=[(joint_a, 1.0), (joint_b, 0.0)],
        )

        data = skin_ref.weights()
        bone_a_idx = data["influences"].index("bone_a")
        bone_b_idx = data["influences"].index("bone_b")

        for w in data["weights"][bone_a_idx]:
            self.assertAlmostEqual(w, 1.0, places=4)
        for w in data["weights"][bone_b_idx]:
            self.assertAlmostEqual(w, 0.0, places=4)

    # ------------------------------------------------------------------
    # add_influence
    # ------------------------------------------------------------------

    def test_add_influence(self):
        skin_ref, _, _, _ = self._make_skin()
        new_joint = cmds.createNode("joint", name="bone_c")
        skin_ref.add_influence(new_joint)

        names = sorted(inf.name() for inf in skin_ref.influences())
        self.assertIn("bone_c", names)


if __name__ == "__main__":
    unittest.main()