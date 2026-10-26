import unittest

import maya.standalone
import mref
from maya import cmds


class TestAnimCurve(unittest.TestCase):

    def setUp(self):
        try:
            maya.standalone.initialize(name='python')
        except RuntimeError:
            pass
        cmds.file(newFile=True, force=True)

    def _make_anim_curve(self):
        cmds.createNode("transform", name="foo")
        cmds.setKeyframe("foo.translateX", time=1, value=0.0)
        cmds.setKeyframe("foo.translateX", time=10, value=5.0)
        cmds.setKeyframe("foo.translateX", time=20, value=2.0)

        curves = cmds.listConnections("foo.translateX", type="animCurve") or []
        return mref.get(curves[0])

    # ------------------------------------------------------------------
    # to_dictionary
    # ------------------------------------------------------------------

    def test_to_dictionary_includes_keys(self):
        ref = self._make_anim_curve()
        data = ref.to_dictionary()
        self.assertIn("keys", data)
        self.assertEqual(len(data["keys"]), 3)

    def test_to_dictionary_includes_metadata(self):
        ref = self._make_anim_curve()
        data = ref.to_dictionary()
        self.assertIn("name", data)
        self.assertIn("animCurveType", data)
        self.assertIn("isWeighted", data)
        self.assertIn("preInfinity", data)
        self.assertIn("postInfinity", data)

    def test_key_data_contains_time_and_value(self):
        ref = self._make_anim_curve()
        data = ref.to_dictionary()
        first = data["keys"][0]
        self.assertIn("time", first)
        self.assertIn("value", first)
        # -- MFnAnimCurve.input(i) returns an MTime; extract the
        # -- numeric value via .value for comparison.
        time_val = (
            first["time"].value
            if hasattr(first["time"], "value")
            else float(first["time"])
        )
        self.assertAlmostEqual(time_val, 1.0, places=4)
        self.assertAlmostEqual(first["value"], 0.0, places=4)

    def test_to_dictionary_tangent_fields_match_flags(self):
        # -- Regression guard: a single batched cmds.keyTangent query
        # -- returns values in Maya's internal flag order, which used
        # -- to scramble these fields (e.g. inWeight held a string).
        ref = self._make_anim_curve()
        cmds.keyTangent(ref.name(), edit=True, index=(0, 0), itt="linear", ott="step")
        key = ref.to_dictionary()["keys"][0]
        self.assertEqual(key["inTangentType"], "linear")
        self.assertEqual(key["outTangentType"], "step")
        self.assertIsInstance(key["inWeight"], float)
        self.assertIsInstance(key["lockTangents"], bool)
        self.assertIsInstance(key["weightedTangents"], bool)

    # ------------------------------------------------------------------
    # construct_from_dictionary round-trip
    # ------------------------------------------------------------------

    @staticmethod
    def _time_value(time):
        # -- to_dictionary stores MFnAnimCurve.input(i) directly, which
        # -- is an MTime for time-based curves.
        return time.value if hasattr(time, "value") else float(time)

    def test_round_trip_preserves_key_values(self):
        # -- Previously skipped: cmds.cutKey(clear=True) deleted the
        # -- curve node. The trait now clears keys through the API.
        ref = self._make_anim_curve()
        original = ref.to_dictionary()
        ref.construct_from_dictionary(original)
        after = ref.to_dictionary()

        self.assertEqual(len(original["keys"]), len(after["keys"]))
        for o_key, a_key in zip(original["keys"], after["keys"]):
            self.assertAlmostEqual(
                self._time_value(o_key["time"]),
                self._time_value(a_key["time"]),
                places=4,
            )
            self.assertAlmostEqual(o_key["value"], a_key["value"], places=4)

    def test_construct_keeps_curve_node(self):
        ref = self._make_anim_curve()
        name = ref.name()
        ref.construct_from_dictionary(ref.to_dictionary())
        self.assertTrue(cmds.objExists(name))
        self.assertEqual(cmds.listConnections("foo.translateX"), [name])

    def test_round_trip_onto_new_driven_key_curve(self):
        # -- Mirrors the aniseed sdk component: store a UU curve's data
        # -- and rebuild it on a freshly created animCurveUU.
        cmds.createNode("transform", name="driver")
        cmds.createNode("transform", name="driven")
        for driver_value, value in ((0, 1), (10, 3)):
            cmds.setDrivenKeyframe(
                "driven.scaleX",
                currentDriver="driver.translateY",
                driverValue=driver_value,
                value=value,
            )
        source = mref.get(cmds.listConnections("driven.scaleX", type="animCurve")[0])
        source.set_tangent_types("linear", "linear")
        data = source.to_dictionary()

        rebuilt = mref.create("animCurveUU", name="rebuilt")
        rebuilt.construct_from_dictionary(data)
        self.assertEqual(rebuilt.key_times(), [0.0, 10.0])
        self.assertEqual(rebuilt.key_values(), [1.0, 3.0])
        self.assertEqual(rebuilt.tangent_types(1), ("linear", "linear"))

    def test_construct_with_empty_dictionary(self):
        # -- The sdk component passes {} when no curve data is stored.
        curve = mref.create("animCurveUU", name="sdk_curve")
        curve.construct_from_dictionary({})
        self.assertEqual(curve.key_count(), 0)

    def test_construct_clears_negative_time_keys(self):
        # -- Regression guard for the cutKey(clear=True) fix. Negative-
        # -- time keys must be wiped before re-applying the new data,
        # -- not preserved as stragglers.
        ref = self._make_anim_curve()

        # Add a stray key at negative time
        cmds.setKeyframe(ref.name(), time=-5, value=99.0)

        # Serialise, drop the negative key from the data, reconstruct
        data = ref.to_dictionary()
        data["keys"] = [
            key
            for key in data["keys"]
            if self._time_value(key["time"]) >= 0
        ]
        ref.construct_from_dictionary(data)

        result = ref.to_dictionary()
        self.assertEqual(len(result["keys"]), 3)
        for key in result["keys"]:
            self.assertGreaterEqual(self._time_value(key["time"]), 0)

    def test_construct_restores_is_weighted(self):
        # -- Regression guard: isWeighted is captured by to_dictionary
        # -- but was historically not restored by construct_from_dictionary.
        ref = self._make_anim_curve()

        data = ref.to_dictionary()
        data["isWeighted"] = True

        ref.construct_from_dictionary(data)
        self.assertTrue(ref.to_dictionary()["isWeighted"])

    # ------------------------------------------------------------------
    # Binding / classification
    # ------------------------------------------------------------------

    def test_binds_to_anim_curve(self):
        ref = self._make_anim_curve()
        self.assertIn("AnimCurve", ref.assigned_traits())

    def test_does_not_bind_to_transform(self):
        self.assertNotIn("AnimCurve", mref.create("transform").assigned_traits())

    def test_curve_type(self):
        ref = self._make_anim_curve()
        self.assertEqual(ref.curve_type(), "TL")
        cmds.setKeyframe("foo.rotateY", time=1, value=10)
        rotate = mref.get(cmds.listConnections("foo.rotateY", type="animCurve")[0])
        self.assertEqual(rotate.curve_type(), "TA")

    def _make_driven_key(self):
        cmds.createNode("transform", name="driver")
        cmds.createNode("transform", name="driven")
        for driver_value, value in ((0, 0), (10, 90)):
            cmds.setDrivenKeyframe(
                "driven.rotateX",
                currentDriver="driver.translateY",
                driverValue=driver_value,
                value=value,
            )
        return mref.get(cmds.listConnections("driven.rotateX", type="animCurve")[0])

    def test_is_driven_key(self):
        self.assertFalse(self._make_anim_curve().is_driven_key())
        driven_key = self._make_driven_key()
        self.assertTrue(driven_key.is_driven_key())
        self.assertEqual(driven_key.curve_type(), "UA")

    # ------------------------------------------------------------------
    # Key queries
    # ------------------------------------------------------------------

    def test_key_count(self):
        self.assertEqual(self._make_anim_curve().key_count(), 3)

    def test_key_times(self):
        self.assertEqual(self._make_anim_curve().key_times(), [1.0, 10.0, 20.0])

    def test_key_values(self):
        self.assertEqual(self._make_anim_curve().key_values(), [0.0, 5.0, 2.0])

    def test_key_values_angular_are_degrees(self):
        driven_key = self._make_driven_key()
        self.assertEqual(driven_key.key_times(), [0.0, 10.0])
        values = driven_key.key_values()
        self.assertAlmostEqual(values[1], 90.0, places=4)

    def test_key_index(self):
        ref = self._make_anim_curve()
        self.assertEqual(ref.key_index(10), 1)
        self.assertIsNone(ref.key_index(11))

    def test_value_at(self):
        ref = self._make_anim_curve()
        self.assertAlmostEqual(ref.value_at(10), 5.0, places=4)
        # -- Constant post infinity holds the last value
        self.assertAlmostEqual(ref.value_at(100), 2.0, places=4)

    def test_value_at_angular_driven_key(self):
        driven_key = self._make_driven_key()
        self.assertAlmostEqual(driven_key.value_at(10), 90.0, places=4)

    # ------------------------------------------------------------------
    # Key editing
    # ------------------------------------------------------------------

    def test_add_key(self):
        ref = self._make_anim_curve()
        index = ref.add_key(30, 7.0, in_tangent_type="linear", out_tangent_type="step")
        self.assertEqual(index, 3)
        self.assertEqual(ref.key_count(), 4)
        self.assertAlmostEqual(ref.value_at(30), 7.0, places=4)
        self.assertEqual(ref.tangent_types(3), ("linear", "step"))

    def test_add_key_replaces_existing(self):
        ref = self._make_anim_curve()
        ref.add_key(10, 9.0)
        self.assertEqual(ref.key_count(), 3)
        self.assertAlmostEqual(ref.value_at(10), 9.0, places=4)

    def test_add_key_angular_uses_degrees(self):
        driven_key = self._make_driven_key()
        driven_key.add_key(5, 45.0)
        self.assertAlmostEqual(cmds.getAttr("driven.rotateX"), 0.0, places=4)
        cmds.setAttr("driver.translateY", 5)
        self.assertAlmostEqual(cmds.getAttr("driven.rotateX"), 45.0, places=4)

    def test_add_key_rejects_unknown_tangent(self):
        ref = self._make_anim_curve()
        with self.assertRaises(ValueError):
            ref.add_key(30, 1.0, in_tangent_type="wobbly")

    def test_insert_key_preserves_shape(self):
        ref = self._make_anim_curve()
        before = ref.value_at(5)
        index = ref.insert_key(5)
        self.assertEqual(index, 1)
        self.assertEqual(ref.key_count(), 4)
        self.assertAlmostEqual(ref.value_at(5), before, places=4)

    def test_insert_key_on_existing_key(self):
        ref = self._make_anim_curve()
        self.assertEqual(ref.insert_key(10), 1)
        self.assertEqual(ref.key_count(), 3)

    def test_remove_key(self):
        ref = self._make_anim_curve()
        self.assertTrue(ref.remove_key(10))
        self.assertEqual(ref.key_times(), [1.0, 20.0])
        self.assertFalse(ref.remove_key(10))

    def test_remove_last_key_keeps_curve(self):
        ref = self._make_anim_curve()
        name = ref.name()
        for time in (1, 10, 20):
            ref.remove_key(time)
        self.assertEqual(ref.key_count(), 0)
        self.assertTrue(cmds.objExists(name))

    def test_offset_keys(self):
        ref = self._make_anim_curve()
        ref.offset_keys(time_offset=5, value_offset=1.0)
        self.assertEqual(ref.key_times(), [6.0, 15.0, 25.0])
        self.assertEqual(ref.key_values(), [1.0, 6.0, 3.0])

    def test_offset_keys_driven_key(self):
        driven_key = self._make_driven_key()
        driven_key.offset_keys(time_offset=2)
        self.assertEqual(driven_key.key_times(), [2.0, 12.0])

    # ------------------------------------------------------------------
    # Tangents / infinity / weighting
    # ------------------------------------------------------------------

    def test_tangent_types_default(self):
        ref = self._make_anim_curve()
        in_type, out_type = ref.tangent_types(0)
        self.assertEqual(
            (in_type, out_type),
            tuple(cmds.keyTangent(ref.name(), query=True, index=(0, 0), itt=True, ott=True)),
        )

    def test_set_tangent_types_all_keys(self):
        ref = self._make_anim_curve()
        ref.set_tangent_types("linear", "linear")
        for index in range(3):
            self.assertEqual(ref.tangent_types(index), ("linear", "linear"))

    def test_set_tangent_types_single_key_and_side(self):
        ref = self._make_anim_curve()
        ref.set_tangent_types("linear", "linear")
        ref.set_tangent_types(out_type="step", index=1)
        self.assertEqual(ref.tangent_types(1), ("linear", "step"))
        self.assertEqual(ref.tangent_types(0), ("linear", "linear"))

    def test_infinity(self):
        ref = self._make_anim_curve()
        self.assertEqual(ref.pre_infinity(), "constant")
        self.assertEqual(ref.post_infinity(), "constant")
        ref.set_pre_infinity("cycle")
        ref.set_post_infinity("oscillate")
        self.assertEqual(ref.pre_infinity(), "cycle")
        self.assertEqual(ref.post_infinity(), "oscillate")
        self.assertEqual(cmds.getAttr(f"{ref.name()}.postInfinity", asString=True), "Oscillate")

    def test_set_infinity_rejects_unknown(self):
        with self.assertRaises(ValueError):
            self._make_anim_curve().set_pre_infinity("forever")

    def test_weighted(self):
        ref = self._make_anim_curve()
        self.assertFalse(ref.is_weighted())
        ref.set_weighted(True)
        self.assertTrue(ref.is_weighted())

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    def test_driven_attributes(self):
        ref = self._make_anim_curve()
        attributes = ref.driven_attributes()
        self.assertIsInstance(attributes, mref.ReferenceList)
        self.assertEqual([a.full_name() for a in attributes], ["|foo.translateX"])

    def test_driven_attributes_skips_unit_conversion(self):
        driven_key = self._make_driven_key()
        self.assertEqual(
            [a.full_name() for a in driven_key.driven_attributes()],
            ["|driven.rotateX"],
        )

    def test_driver_attribute(self):
        self.assertIsNone(self._make_anim_curve().driver_attribute())
        driver = self._make_driven_key().driver_attribute()
        self.assertEqual(driver.full_name(), "|driver.translateY")


if __name__ == "__main__":
    unittest.main()