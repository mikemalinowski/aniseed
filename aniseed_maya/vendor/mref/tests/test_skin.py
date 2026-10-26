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

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_skin_cluster(self):
        skin_ref, _, _, _ = self._make_skin()
        self.assertIn("SkinCluster", skin_ref.assigned_traits())

    def test_does_not_bind_to_cluster(self):
        cube = cmds.polyCube()[0]
        cluster = cmds.cluster(cube)[0]
        self.assertNotIn("SkinCluster", mref.get(cluster).assigned_traits())

    # ------------------------------------------------------------------
    # influence management
    # ------------------------------------------------------------------

    def _weight_all_to(self, skin_ref, mesh, joint):
        others = [i.name() for i in skin_ref.influences() if i.name() != joint]
        cmds.skinPercent(
            skin_ref.full_name(),
            f"{mesh}.vtx[*]",
            transformValue=[(joint, 1.0)] + [(o, 0.0) for o in others],
        )

    def test_remove_influence(self):
        skin_ref, _, _, joint_b = self._make_skin()
        skin_ref.remove_influence(joint_b)
        self.assertEqual([i.name() for i in skin_ref.influences()], ["bone_a"])

    def test_unused_influences(self):
        skin_ref, mesh, joint_a, _ = self._make_skin()
        self._weight_all_to(skin_ref, mesh, joint_a)
        self.assertEqual(skin_ref.unused_influences().names(), ["bone_b"])

    def test_remove_unused_influences(self):
        skin_ref, mesh, joint_a, _ = self._make_skin()
        self._weight_all_to(skin_ref, mesh, joint_a)
        removed = skin_ref.remove_unused_influences()
        self.assertEqual(removed.names(), ["bone_b"])
        self.assertEqual([i.name() for i in skin_ref.influences()], ["bone_a"])

    # ------------------------------------------------------------------
    # single influence / single component weights
    # ------------------------------------------------------------------

    def test_influence_weights(self):
        skin_ref, mesh, joint_a, _ = self._make_skin()
        self._weight_all_to(skin_ref, mesh, joint_a)
        self.assertEqual(skin_ref.influence_weights("bone_a"), [1.0] * 8)
        self.assertEqual(skin_ref.influence_weights("bone_b"), [0.0] * 8)

    def test_influence_weights_after_middle_influence_removed(self):
        # -- Guards that influence positions (not matrix indices) are used
        skin_ref, mesh, _, _ = self._make_skin()
        bone_c = cmds.createNode("joint", name="bone_c")
        skin_ref.add_influence(bone_c)
        self._weight_all_to(skin_ref, mesh, bone_c)
        skin_ref.remove_influence("bone_b")
        self.assertEqual(skin_ref.influence_weights("bone_c"), [1.0] * 8)

    def test_set_influence_weights_normalizes(self):
        skin_ref, mesh, joint_a, _ = self._make_skin()
        self._weight_all_to(skin_ref, mesh, joint_a)
        skin_ref.set_influence_weights("bone_b", [0.25] * 8)
        for w in skin_ref.influence_weights("bone_b"):
            self.assertAlmostEqual(w, 0.25, places=4)
        for w in skin_ref.influence_weights("bone_a"):
            self.assertAlmostEqual(w, 0.75, places=4)

    def test_set_influence_weights_wrong_length_raises(self):
        skin_ref, _, _, _ = self._make_skin()
        with self.assertRaises(ValueError):
            skin_ref.set_influence_weights("bone_a", [1.0])

    def test_influence_weights_unknown_influence_raises(self):
        skin_ref, _, _, _ = self._make_skin()
        other = cmds.createNode("joint", name="not_bound")
        with self.assertRaises(ValueError):
            skin_ref.influence_weights(other)

    def test_component_weights_round_trip(self):
        skin_ref, _, _, _ = self._make_skin()
        skin_ref.set_component_weights(3, {"bone_a": 0.2, "bone_b": 0.8})
        weights = skin_ref.component_weights(3)
        self.assertAlmostEqual(weights["bone_a"], 0.2, places=4)
        self.assertAlmostEqual(weights["bone_b"], 0.8, places=4)

    def test_set_component_weights_zeroes_unlisted(self):
        skin_ref, _, _, _ = self._make_skin()
        skin_ref.set_component_weights(0, {"bone_b": 1.0})
        self.assertEqual(list(skin_ref.component_weights(0).keys()), ["bone_b"])

    def test_copy_weights_to(self):
        skin_ref, mesh, _, joint_b = self._make_skin()
        self._weight_all_to(skin_ref, mesh, joint_b)

        other_mesh = cmds.polyCube(name="other")[0]
        other_skin = mref.get(cmds.skinCluster("bone_a", other_mesh, toSelectedBones=True)[0])
        skin_ref.copy_weights_to(other_skin)

        self.assertIn("bone_b", [i.name() for i in other_skin.influences()])
        for w in other_skin.influence_weights("bone_b"):
            self.assertAlmostEqual(w, 1.0, places=4)

    # ------------------------------------------------------------------
    # weight maintenance
    # ------------------------------------------------------------------

    def test_max_influences(self):
        skin_ref, _, _, _ = self._make_skin()
        skin_ref.set_max_influences(2, maintain=True)
        self.assertEqual(skin_ref.max_influences(), 2)
        self.assertTrue(cmds.getAttr(f"{skin_ref.full_name()}.maintainMaxInfluences"))
        skin_ref.set_max_influences(3, maintain=False)
        self.assertEqual(skin_ref.max_influences(), 3)
        self.assertFalse(cmds.getAttr(f"{skin_ref.full_name()}.maintainMaxInfluences"))

    def test_prune_weights(self):
        skin_ref, _, _, _ = self._make_skin()
        skin_ref.set_component_weights(0, {"bone_a": 0.95, "bone_b": 0.05})
        skin_ref.prune_weights(0.1)
        weights = skin_ref.component_weights(0)
        self.assertEqual(list(weights.keys()), ["bone_a"])
        self.assertAlmostEqual(weights["bone_a"], 1.0, places=4)

    def test_normalize_weights(self):
        skin_ref, _, _, _ = self._make_skin()
        skin_ref.set_normalization_mode("none")
        skin_ref.set_component_weights(0, {"bone_a": 0.2, "bone_b": 0.2}, normalize=False)
        skin_ref.normalize_weights()
        weights = skin_ref.component_weights(0)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)

    def test_normalization_mode(self):
        skin_ref, _, _, _ = self._make_skin()
        self.assertEqual(skin_ref.normalization_mode(), "interactive")
        skin_ref.set_normalization_mode("post")
        self.assertEqual(skin_ref.normalization_mode(), "post")
        skin_ref.set_normalization_mode(0)
        self.assertEqual(skin_ref.normalization_mode(), "none")
        with self.assertRaises(ValueError):
            skin_ref.set_normalization_mode("bogus")

    def test_skinning_method(self):
        skin_ref, _, _, _ = self._make_skin()
        self.assertEqual(skin_ref.skinning_method(), "linear")
        skin_ref.set_skinning_method("dual_quaternion")
        self.assertEqual(skin_ref.skinning_method(), "dual_quaternion")
        skin_ref.set_skinning_method(2)
        self.assertEqual(skin_ref.skinning_method(), "blended")

    # ------------------------------------------------------------------
    # bind pose
    # ------------------------------------------------------------------

    def test_bind_pose(self):
        skin_ref, _, _, _ = self._make_skin()
        pose = skin_ref.bind_pose()
        self.assertIsNotNone(pose)
        self.assertEqual(cmds.nodeType(pose.full_name()), "dagPose")

    def test_go_to_bind_pose(self):
        skin_ref, _, _, joint_b = self._make_skin()
        cmds.setAttr(f"{joint_b}.translateX", 5)
        skin_ref.go_to_bind_pose()
        self.assertAlmostEqual(cmds.getAttr(f"{joint_b}.translateX"), 0.0, places=4)

    def test_go_to_bind_pose_raises_without_pose(self):
        skin_ref, _, _, _ = self._make_skin()
        cmds.delete(skin_ref.bind_pose().full_name())
        self.assertIsNone(skin_ref.bind_pose())
        with self.assertRaises(RuntimeError):
            skin_ref.go_to_bind_pose()

    def test_unbind(self):
        skin_ref, mesh, _, _ = self._make_skin()
        skin_name = skin_ref.full_name()
        skin_ref.unbind()
        self.assertFalse(cmds.objExists(skin_name))
        self.assertFalse(cmds.ls(cmds.listHistory(mesh), type="skinCluster"))


if __name__ == "__main__":
    unittest.main()