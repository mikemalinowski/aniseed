import unittest

import maya.standalone
import mref
from maya import cmds
from maya import mel


class TestNucleusObject(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_cloth(self):
        plane = cmds.polyPlane(sx=4, sy=4, name="clothPlane")[0]
        cmds.select(plane)
        try:
            cloth = mel.eval("createNCloth 0")
        except RuntimeError as exc:
            self.skipTest(f"nCloth creation failed in standalone: {exc}")
        if not cloth:
            self.skipTest("nCloth creation returned nothing")
        return mref.get(cloth[0]), plane

    def _make_rigid(self):
        sphere = cmds.polySphere(name="collider")[0]
        cmds.select(sphere)
        try:
            rigid = mel.eval("makeCollideNCloth")
        except RuntimeError as exc:
            self.skipTest(f"nRigid creation failed in standalone: {exc}")
        if not rigid:
            self.skipTest("nRigid creation returned nothing")
        return mref.get(rigid[0]), sphere

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_nbase_and_hair(self):
        for node_type in ("nCloth", "nRigid", "nParticle", "hairSystem"):
            node = mref.get(cmds.createNode(node_type))
            self.assertIn("NucleusObject", node.assigned_traits(), node_type)

    def test_does_not_bind_to_unrelated_nodes(self):
        for node_type in ("nucleus", "particle", "transform"):
            node = mref.get(cmds.createNode(node_type))
            self.assertNotIn("NucleusObject", node.assigned_traits(), node_type)
        mesh = cmds.listRelatives(cmds.polyCube()[0], shapes=True, fullPath=True)[0]
        self.assertNotIn("NucleusObject", mref.get(mesh).assigned_traits())

    # ------------------------------------------------------------------
    # solver / is_passive / set_solver
    # ------------------------------------------------------------------

    def test_solver(self):
        cloth, _ = self._make_cloth()
        solver = cloth.solver()
        self.assertIsNotNone(solver)
        self.assertEqual(solver.node_type(), "nucleus")

    def test_solver_none_when_unconnected(self):
        self.assertIsNone(mref.get(cmds.createNode("nCloth")).solver())

    def test_is_passive(self):
        cloth, _ = self._make_cloth()
        rigid, _ = self._make_rigid()
        self.assertFalse(cloth.is_passive())
        self.assertTrue(rigid.is_passive())

    def test_set_solver_moves_active_object(self):
        cloth, _ = self._make_cloth()
        old_solver = cloth.solver()
        new_solver = cmds.createNode("nucleus", name="otherNucleus")
        cloth.set_solver(new_solver)
        self.assertEqual(cloth.solver().name(), "otherNucleus")
        self.assertFalse(
            cmds.listConnections(old_solver.full_name(), type="nCloth") or []
        )
        self.assertTrue(cmds.isConnected("otherNucleus.outputObjects[0]", f"{cloth.full_name()}.nextState"))
        self.assertTrue(cmds.isConnected("otherNucleus.startFrame", f"{cloth.full_name()}.startFrame"))
        self.assertFalse(cloth.is_passive())

    def test_set_solver_keeps_passive(self):
        rigid, _ = self._make_rigid()
        new_solver = cmds.createNode("nucleus", name="otherNucleus")
        rigid.set_solver(new_solver)
        self.assertEqual(rigid.solver().name(), "otherNucleus")
        self.assertTrue(rigid.is_passive())

    def test_set_solver_on_fresh_hair_system(self):
        hair = mref.get(cmds.createNode("hairSystem"))
        solver = cmds.createNode("nucleus", name="hairNucleus")
        hair.set_solver(solver)
        self.assertEqual(hair.solver().name(), "hairNucleus")
        self.assertFalse(hair.is_passive())

    def test_set_solver_uses_free_index(self):
        cloth, _ = self._make_cloth()
        solver = cloth.solver().full_name()
        hair = mref.get(cmds.createNode("hairSystem"))
        hair.set_solver(solver)
        self.assertTrue(cmds.isConnected(f"{hair.full_name()}.currentState", f"{solver}.inputActive[1]"))
        self.assertTrue(cmds.isConnected(f"{solver}.outputObjects[1]", f"{hair.full_name()}.nextState"))

    # ------------------------------------------------------------------
    # enable / disable / is_enabled
    # ------------------------------------------------------------------

    def test_enable_disable_nbase(self):
        cloth = mref.get(cmds.createNode("nCloth"))
        self.assertTrue(cloth.is_enabled())
        cloth.disable()
        self.assertFalse(cloth.is_enabled())
        cloth.enable()
        self.assertTrue(cloth.is_enabled())

    def test_enable_disable_hair_system(self):
        hair = mref.get(cmds.createNode("hairSystem"))
        hair.disable()
        self.assertFalse(hair.is_enabled())
        self.assertEqual(cmds.getAttr(f"{hair.full_name()}.simulationMethod"), 0)
        hair.enable()
        self.assertTrue(hair.is_enabled())
        self.assertEqual(cmds.getAttr(f"{hair.full_name()}.simulationMethod"), 3)

    def test_enable_hair_keeps_existing_method(self):
        hair = mref.get(cmds.createNode("hairSystem"))
        cmds.setAttr(f"{hair.full_name()}.simulationMethod", 1)
        hair.enable()
        self.assertEqual(cmds.getAttr(f"{hair.full_name()}.simulationMethod"), 1)

    # ------------------------------------------------------------------
    # input_mesh / output_mesh
    # ------------------------------------------------------------------

    def test_input_mesh(self):
        cloth, plane = self._make_cloth()
        self.assertEqual(cloth.input_mesh().parent().name(), plane)

    def test_rigid_input_mesh(self):
        rigid, sphere = self._make_rigid()
        self.assertEqual(rigid.input_mesh().parent().name(), sphere)

    def test_output_mesh(self):
        cloth, _ = self._make_cloth()
        output = cloth.output_mesh()
        self.assertIsNotNone(output)
        self.assertEqual(output.node_type(), "mesh")

    def test_mesh_none_when_not_applicable(self):
        hair = mref.get(cmds.createNode("hairSystem"))
        self.assertIsNone(hair.input_mesh())
        self.assertIsNone(hair.output_mesh())
        rigid, _ = self._make_rigid()
        self.assertIsNone(rigid.output_mesh())

    # ------------------------------------------------------------------
    # hair_follicles
    # ------------------------------------------------------------------

    def test_hair_follicles(self):
        hair = mref.get(cmds.createNode("hairSystem"))
        follicle_a = cmds.createNode("follicle", name="follicleShapeA")
        follicle_b = cmds.createNode("follicle", name="follicleShapeB")
        cmds.connectAttr(f"{follicle_a}.outHair", f"{hair.full_name()}.inputHair[0]")
        cmds.connectAttr(f"{follicle_b}.outHair", f"{hair.full_name()}.inputHair[1]")
        follicles = hair.hair_follicles()
        self.assertIsInstance(follicles, mref.ReferenceList)
        self.assertEqual(follicles.names(), ["follicleShapeA", "follicleShapeB"])

    def test_hair_follicles_empty_for_cloth(self):
        self.assertEqual(len(mref.get(cmds.createNode("nCloth")).hair_follicles()), 0)


if __name__ == "__main__":
    unittest.main()
