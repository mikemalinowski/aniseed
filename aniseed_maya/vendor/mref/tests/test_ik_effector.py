import unittest

import maya.standalone
import mref
from maya import cmds


class TestIkEffector(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_chain(self):
        cmds.select(clear=True)
        root = cmds.joint(name="root", position=(0, 0, 0))
        mid = cmds.joint(name="mid", position=(0, 5, 1))
        tip = cmds.joint(name="tip", position=(0, 10, 0))
        handle, effector = cmds.ikHandle(startJoint=root, endEffector=tip)
        return mref.get(effector), mref.get(handle), root, mid, tip

    # ------------------------------------------------------------------
    # binding
    # ------------------------------------------------------------------

    def test_binds_to_effector(self):
        effector, _, _, _, _ = self._make_chain()
        self.assertIn("IkEffector", effector.assigned_traits())
        self.assertIn("Transform", effector.assigned_traits())

    def test_does_not_bind_to_handle_or_joint(self):
        _, handle, root, _, _ = self._make_chain()
        self.assertNotIn("IkEffector", handle.assigned_traits())
        self.assertNotIn("IkEffector", mref.get(root).assigned_traits())

    # ------------------------------------------------------------------
    # ik handle
    # ------------------------------------------------------------------

    def test_ik_handle(self):
        effector, handle, _, _, _ = self._make_chain()
        self.assertEqual(effector.ik_handle(), handle)

    def test_ik_handles(self):
        effector, handle, _, _, _ = self._make_chain()
        handles = effector.ik_handles()
        self.assertIsInstance(handles, mref.ReferenceList)
        self.assertEqual(len(handles), 1)
        self.assertEqual(handles[0], handle)

    def test_round_trip_with_handle(self):
        effector, handle, _, _, _ = self._make_chain()
        self.assertEqual(handle.effector(), effector)

    # ------------------------------------------------------------------
    # joints
    # ------------------------------------------------------------------

    def test_end_joint(self):
        effector, _, _, _, tip = self._make_chain()
        self.assertEqual(effector.end_joint().name(), tip)

    def test_start_joint(self):
        effector, _, root, _, _ = self._make_chain()
        self.assertEqual(effector.start_joint().name(), root)

    # ------------------------------------------------------------------
    # disconnected
    # ------------------------------------------------------------------

    def test_disconnected_effector(self):
        effector = mref.create("ikEffector")
        self.assertIsNone(effector.ik_handle())
        self.assertEqual(len(effector.ik_handles()), 0)
        self.assertIsNone(effector.end_joint())
        self.assertIsNone(effector.start_joint())


if __name__ == "__main__":
    unittest.main()
