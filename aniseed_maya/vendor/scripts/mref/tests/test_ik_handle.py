import unittest

import maya.standalone
import mref
from maya import cmds


class TestIkHandle(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_ik(self, solver="ikRPsolver"):
        cmds.select(clear=True)
        a = cmds.joint(name="jnt_a", position=(0, 0, 0))
        b = cmds.joint(name="jnt_b", position=(2, 0, -0.5))
        c = cmds.joint(name="jnt_c", position=(4, 0, 0))
        cmds.select(clear=True)
        handle, effector = cmds.ikHandle(
            name="ik_hdl",
            startJoint=a,
            endEffector=c,
            solver=solver,
        )
        return mref.get(handle), a, b, c

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_ik_handle(self):
        handle, _, _, _ = self._make_ik()
        self.assertIn("IkHandle", handle.assigned_traits())

    def test_does_not_bind_to_joint(self):
        _, a, _, _ = self._make_ik()
        self.assertNotIn("IkHandle", mref.get(a).assigned_traits())

    # ------------------------------------------------------------------
    # chain
    # ------------------------------------------------------------------

    def test_start_joint(self):
        handle, _, _, _ = self._make_ik()
        self.assertEqual(handle.start_joint().name(), "jnt_a")

    def test_end_joint(self):
        handle, _, _, _ = self._make_ik()
        self.assertEqual(handle.end_joint().name(), "jnt_c")

    def test_effector(self):
        handle, _, _, _ = self._make_ik()
        effector = handle.effector()
        self.assertIsNotNone(effector)
        self.assertEqual(effector.node_type(), "ikEffector")

    def test_joint_chain(self):
        handle, _, _, _ = self._make_ik()
        chain = handle.joint_chain()
        self.assertIsInstance(chain, mref.ReferenceList)
        self.assertEqual(chain.names(), ["jnt_a", "jnt_b", "jnt_c"])

    # ------------------------------------------------------------------
    # solver
    # ------------------------------------------------------------------

    def test_solver_type(self):
        handle, _, _, _ = self._make_ik()
        self.assertEqual(handle.solver_type(), "ikRPsolver")

    def test_set_solver_type(self):
        handle, _, _, _ = self._make_ik()
        handle.set_solver_type("ikSCsolver")
        self.assertEqual(handle.solver_type(), "ikSCsolver")

    # ------------------------------------------------------------------
    # pole vector / twist
    # ------------------------------------------------------------------

    def test_pole_vector_round_trip(self):
        handle, _, _, _ = self._make_ik()
        handle.set_pole_vector([0.0, 1.0, 0.0])
        result = handle.pole_vector()
        for actual, expected in zip(result, [0.0, 1.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=4)

    def test_add_pole_vector_constraint(self):
        handle, _, _, _ = self._make_ik()
        target = cmds.createNode("transform", name="pv_target")
        cmds.setAttr(f"{target}.translate", 2, 0, -5)
        constraint = handle.add_pole_vector_constraint(target)
        self.assertEqual(constraint.node_type(), "poleVectorConstraint")
        self.assertIn("Constraint", constraint.assigned_traits())
        self.assertEqual(constraint.drivers().names(), ["pv_target"])

    def test_twist_round_trip(self):
        handle, _, _, _ = self._make_ik()
        handle.set_twist(45.0)
        self.assertAlmostEqual(handle.twist(), 45.0, places=4)


if __name__ == "__main__":
    unittest.main()
