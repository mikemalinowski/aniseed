import os
import json
import tempfile
import unittest
import xstack

COMPONENT_PATH = os.path.join(
    os.path.dirname(__file__),
)

class TestUnitStack(unittest.TestCase):
    counter = 0
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_can_instance_stack(self):

        stack = xstack.Stack()

        self.assertIsNotNone(stack)

    def test_can_find_components(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        self.assertGreater(
            len(stack.component_library.plugins()),
            0,
        )

    def test_can_add_component(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="test",
            component_type="MinimalComponent",
        )

        self.assertIsNotNone(component)

        self.assertIn(
            component,
            stack.components(),
        )

    def test_can_remove_component(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="test",
            component_type="MinimalComponent",
        )

        stack.remove_component(component)

        self.assertNotIn(
            component,
            stack.components(),
        )

    def test_can_build_stack(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        test_component = stack.component_library.request("RunTestComponent")
        test_component.RUN_ORDER = []

        component = stack.add_component(
            label="test",
            component_type="RunTestComponent",
        )

        stack.build()

        self.assertGreater(
            len(test_component.RUN_ORDER),
            0,
        )

    def test_basic_build_order_stack(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        test_component = stack.component_library.request("RunTestComponent")
        test_component.RUN_ORDER = []

        component_a = stack.add_component(
            label="test",
            component_type="RunTestComponent",
        )

        component_b = stack.add_component(
            label="test",
            component_type="RunTestComponent",
        )

        stack.build()

        self.assertEqual(
            component_a,
            test_component.RUN_ORDER[0],
        )

        self.assertEqual(
            component_b,
            test_component.RUN_ORDER[1],
        )

    def test_adjust_build_order_stack(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        test_component = stack.component_library.request("RunTestComponent")
        test_component.RUN_ORDER = []

        component_a = stack.add_component(
            label="test a",
            component_type="RunTestComponent",
        )

        component_b = stack.add_component(
            label="test b",
            component_type="RunTestComponent",
        )

        component_a.set_parent(
            parent=None,
            child_index=1
        )

        stack.build()

        self.assertEqual(
            component_b,
            test_component.RUN_ORDER[0],
        )

        self.assertEqual(
            component_a,
            test_component.RUN_ORDER[1],
        )

    def test_adjust_build_parent_stack(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        test_component = stack.component_library.request("RunTestComponent")
        test_component.RUN_ORDER = []

        component_a = stack.add_component(
            label="test a",
            component_type="RunTestComponent",
        )

        component_b = stack.add_component(
            label="test b",
            component_type="RunTestComponent",
        )

        component_a.set_parent(parent=component_b)

        stack.build()

        self.assertEqual(
            component_b,
            test_component.RUN_ORDER[0],
        )

        self.assertEqual(
            component_a,
            test_component.RUN_ORDER[1],
        )

    def test_invalid_component(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        stack.add_component(label="", component_type="InvalidComponent")

        result = stack.build()

        self.assertFalse(result)

    def test_invalid_requirement(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        stack.add_component(label="", component_type="ComponentWithExpectedRequirementNotSet")

        result = stack.build()

        self.assertFalse(result)

    def test_valid_input(self):

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(label="", component_type="ComponentWithExpectedRequirementNotSet")

        component.input("expected_requirement").set(True)

        result = stack.build()

        self.assertTrue(result)

    def test_not_executed_status(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="MinimalComponent",
        )

        self.assertEqual(
            component.status(),
            xstack.constants.Status.NotExecuted,
        )

    def test_executed_successfully_status(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="MinimalComponent",
        )
        stack.build()

        self.assertEqual(
            component.status(),
            xstack.constants.Status.Success,
        )

    def test_execution_failed_status(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="FailingComponent",
        )
        stack.build()

        self.assertEqual(
            component.status(),
            xstack.constants.Status.Failed,
        )

    def test_invalid_status(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="ComponentWithExpectedRequirementNotSet",
        )
        stack.build()

        self.assertEqual(
            component.status(),
            xstack.constants.Status.Invalid,
        )

    def test_option_setting(self):
        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        component = stack.add_component(
            label="",
            component_type="ComponentWithOption",
        )

        component.option("test_option").set("bar")

        result = stack.build()

        self.assertTrue(
            result
        )

    def test_progression(self):
        self._reset_counter()

        stack = xstack.Stack(
            component_paths=[COMPONENT_PATH],
        )

        for i in range(1, 10):
            stack.add_component(
                label="",
                component_type="ComponentWithOption",
                options={"test_option": "bar"},
            )

        stack.build_progressed.connect(self._increment_counter)
        result = stack.build()

        self.assertEqual(
            self.counter,
            10,
        )

    def _reset_counter(self):
        counter = 0

    def _increment_counter(self, *args, **kwargs):
        self.counter += 1


# ------------------------------------------------------------------------------
class TestDuplicate(unittest.TestCase):
    """
    Tests for Component.duplicate, in particular that each duplicate is
    parented under its final parent before its on_enter_stack runs.
    """

    def _make_nested(self):
        stack = xstack.Stack(component_paths=[COMPONENT_PATH])
        top = stack.add_component(label="Top LF", component_type="ParentHookingComponent")
        middle = stack.add_component(label="Middle LF", component_type="ParentHookingComponent", parent=top)
        bottom = stack.add_component(label="Bottom LF", component_type="ParentHookingComponent", parent=middle)
        return stack, top, middle, bottom

    def test_duplicate_is_sibling_by_default(self):
        stack, top, middle, bottom = self._make_nested()
        root = stack.add_component(label="Root", component_type="MinimalComponent")
        top.set_parent(root)

        duplicate = top.duplicate()

        self.assertIs(duplicate.parent, root)
        self.assertIs(duplicate.parent_on_enter, root)

    def test_children_enter_stack_under_the_duplicated_parent(self):
        stack, top, middle, bottom = self._make_nested()

        top_twin = top.duplicate(search_for="LF", replace_with="RT")
        middle_twin = top_twin.children[0]
        bottom_twin = middle_twin.children[0]

        self.assertEqual(
            [top_twin.label(), middle_twin.label(), bottom_twin.label()],
            ["Top RT", "Middle RT", "Bottom RT"],
        )

        # -- Each duplicate saw its duplicated parent when it entered the stack
        self.assertIs(middle_twin.parent_on_enter, top_twin)
        self.assertIs(bottom_twin.parent_on_enter, middle_twin)

        # -- So hooking to the parent connects to the duplicated parent
        self.assertEqual(middle_twin.input("Parent").get(resolved=False), "[Top RT].[output].[Control]")
        self.assertEqual(bottom_twin.input("Parent").get(resolved=False), "[Middle RT].[output].[Control]")

        # -- The originals are untouched
        self.assertEqual(top.children, [middle])
        self.assertEqual(middle.children, [bottom])
        self.assertEqual(middle.input("Parent").get(resolved=False), "[Top LF].[output].[Control]")

    def test_duplicate_under_an_explicit_parent(self):
        stack, top, middle, bottom = self._make_nested()
        other = stack.add_component(label="Other", component_type="ParentHookingComponent")

        duplicate = middle.duplicate(parent=other)

        self.assertIs(duplicate.parent, other)
        self.assertIs(duplicate.parent_on_enter, other)
        self.assertIs(duplicate.children[0].parent_on_enter, duplicate)
        self.assertNotIn(duplicate, top.children)

    def test_duplicate_without_children(self):
        stack, top, middle, bottom = self._make_nested()

        duplicate = middle.duplicate(include_children=False)

        self.assertEqual(duplicate.children, [])
        self.assertIs(duplicate.parent, top)


# ------------------------------------------------------------------------------
class TestAdditionalData(unittest.TestCase):
    """
    Tests for the on_serialise / on_deserialise hooks.
    """

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _make_stack(self):
        return xstack.Stack(component_paths=[COMPONENT_PATH])

    def _make_tree(self, stack):
        root = stack.add_component(label="root", component_type="AdditionalDataComponent")
        child = stack.add_component(label="child", component_type="AdditionalDataComponent", parent=root)
        root.payload = {"name": "root", "values": [1, 2, 3]}
        child.payload = {"name": "child"}
        return root, child

    def test_serialise_includes_additional_data(self):
        stack = self._make_stack()
        root, child = self._make_tree(stack)

        data = stack.serialise()

        self.assertEqual(data["tree"][0]["additional_data"], {"name": "root", "values": [1, 2, 3]})
        self.assertEqual(data["tree"][0]["children"][0]["additional_data"], {"name": "child"})

    def test_deserialise_passes_additional_data_back(self):
        stack = self._make_stack()
        self._make_tree(stack)
        data = stack.serialise()

        loaded = self._make_stack()
        loaded.deserialise(data)

        root = loaded.root_components[0]
        self.assertEqual(root.received, {"name": "root", "values": [1, 2, 3]})
        self.assertEqual(root.children[0].received, {"name": "child"})

    def test_on_deserialise_runs_before_children_are_added(self):
        stack = self._make_stack()
        self._make_tree(stack)
        data = stack.serialise()

        children_when_called = []
        original = xstack.Component.deserialise_additional_data

        def record(component, additional_data):
            children_when_called.append((component.label(), len(component.children)))
            return original(component, additional_data)

        xstack.Component.deserialise_additional_data = record
        try:
            self._make_stack().deserialise(data)
        finally:
            xstack.Component.deserialise_additional_data = original

        self.assertEqual(children_when_called, [("root", 0), ("child", 0)])

    def test_missing_additional_data_gives_an_empty_dictionary(self):
        stack = self._make_stack()
        self._make_tree(stack)
        data = stack.serialise()

        # -- Data saved before this was supported has no additional_data
        del data["tree"][0]["additional_data"]
        del data["tree"][0]["children"][0]["additional_data"]

        loaded = self._make_stack()
        loaded.deserialise(data)

        self.assertEqual(loaded.root_components[0].received, {})
        self.assertEqual(loaded.root_components[0].children[0].received, {})

    def test_failing_hooks_do_not_break_serialising_or_loading(self):
        stack = self._make_stack()
        stack.add_component(label="failing", component_type="FailingAdditionalDataComponent")
        good = stack.add_component(label="good", component_type="AdditionalDataComponent")
        good.payload = {"kept": True}

        data = stack.serialise()
        self.assertEqual(data["tree"][0]["additional_data"], {})

        loaded = self._make_stack()
        loaded.deserialise(data)

        self.assertEqual(len(loaded.components()), 2)
        self.assertEqual(loaded.root_components[1].received, {"kept": True})

    def test_import_subtree_passes_additional_data(self):
        stack = self._make_stack()
        root, child = self._make_tree(stack)
        filepath = os.path.join(self.tmp_dir.name, "subtree.json")
        root.save_settings(filepath)

        target_stack = self._make_stack()
        target = target_stack.add_component(label="target", component_type="MinimalComponent")
        target.import_subtree(filepath)

        imported = target.children[0]
        self.assertEqual(imported.received, {"name": "root", "values": [1, 2, 3]})
        self.assertEqual(imported.children[0].received, {"name": "child"})

    def test_load_settings_passes_additional_data(self):
        stack = self._make_stack()
        root, child = self._make_tree(stack)
        filepath = os.path.join(self.tmp_dir.name, "settings.json")
        child.save_settings(filepath)

        other = self._make_stack().add_component(label="other", component_type="AdditionalDataComponent")
        other.load_settings(filepath)

        self.assertEqual(other.received, {"name": "child"})


# ------------------------------------------------------------------------------
class TestImportSubtree(unittest.TestCase):
    """
    Tests for Stack.import_subtree_under and Component.import_subtree —
    the save-subset-then-load-under-a-parent workflow.
    """

    def setUp(self):
        # -- A temp directory for any JSON files written by these tests.
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------

    def _make_stack(self):
        return xstack.Stack(component_paths=[COMPONENT_PATH])

    def _tmp_json(self, name="subtree.json"):
        return os.path.join(self.tmp_path, name)

    # --------------------------------------------------------------------------
    # Single-component export → import-under-parent
    # --------------------------------------------------------------------------

    def test_import_subtree_under_adds_loaded_component_as_child(self):
        # -- Set up source stack with one component to export
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        # -- Set up destination stack with a target parent
        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        # -- Import
        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        # -- Target should now have exactly one child with the source label
        self.assertEqual(len(target_parent.children), 1)
        self.assertEqual(target_parent.children[0].label(), "source_component")

    def test_import_subtree_regenerates_uuid(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )
        source_uuid = source_component.uuid()

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported = target_parent.children[0]
        self.assertNotEqual(
            imported.uuid(),
            source_uuid,
            "Imported component must get a fresh UUID, not the source's UUID.",
        )

    def test_import_subtree_preserves_option_values(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="ComponentWithOption",
        )
        source_component.option("test_option").set("custom_value")

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported = target_parent.children[0]
        self.assertEqual(
            imported.option("test_option").get(),
            "custom_value",
        )

    def test_import_subtree_preserves_input_values(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="ComponentWithExpectedRequirementSet",
        )
        source_component.input("expected_requirement").set(42)

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported = target_parent.children[0]
        self.assertEqual(
            imported.input("expected_requirement").get(),
            42,
        )

    def test_import_subtree_preserves_disabled_state(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )
        source_component.set_enabled(False)

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported = target_parent.children[0]
        self.assertFalse(imported.is_enabled())

    # --------------------------------------------------------------------------
    # Recursive subtree
    # --------------------------------------------------------------------------

    def test_import_subtree_preserves_child_hierarchy(self):
        # -- Build a 3-deep subtree on the source side
        source_stack = self._make_stack()
        root = source_stack.add_component(
            label="root",
            component_type="MinimalComponent",
        )
        child = source_stack.add_component(
            label="child",
            component_type="MinimalComponent",
            parent=root,
        )
        grandchild = source_stack.add_component(
            label="grandchild",
            component_type="MinimalComponent",
            parent=child,
        )

        filepath = self._tmp_json()
        root.save_settings(filepath)

        # -- Import into a fresh stack
        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported_root = target_parent.children[0]
        self.assertEqual(imported_root.label(), "root")
        self.assertEqual(len(imported_root.children), 1)

        imported_child = imported_root.children[0]
        self.assertEqual(imported_child.label(), "child")
        self.assertEqual(len(imported_child.children), 1)

        imported_grandchild = imported_child.children[0]
        self.assertEqual(imported_grandchild.label(), "grandchild")
        self.assertEqual(len(imported_grandchild.children), 0)

    def test_import_subtree_regenerates_uuids_through_full_depth(self):
        source_stack = self._make_stack()
        root = source_stack.add_component(
            label="root",
            component_type="MinimalComponent",
        )
        child = source_stack.add_component(
            label="child",
            component_type="MinimalComponent",
            parent=root,
        )

        source_uuids = {root.uuid(), child.uuid()}

        filepath = self._tmp_json()
        root.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )
        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported_uuids = {
            target_parent.children[0].uuid(),
            target_parent.children[0].children[0].uuid(),
        }

        self.assertEqual(
            len(source_uuids & imported_uuids),
            0,
            "No imported component should share a UUID with the source.",
        )

    # --------------------------------------------------------------------------
    # parent=None case
    # --------------------------------------------------------------------------

    def test_import_subtree_under_none_parent_adds_as_root_components(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        # -- Destination stack starts empty
        self.assertEqual(len(dest_stack.root_components), 0)

        dest_stack.import_subtree_under(parent=None, filepath=filepath)

        # -- The imported component should now be a root component
        self.assertEqual(len(dest_stack.root_components), 1)
        self.assertEqual(dest_stack.root_components[0].label(), "source_component")

    # --------------------------------------------------------------------------
    # Full-stack file shape (Stack.save output)
    # --------------------------------------------------------------------------

    def test_import_subtree_under_accepts_full_stack_file(self):
        # -- A stack-format file (with "tree" key) has multiple roots
        source_stack = self._make_stack()
        source_stack.add_component(label="root_a", component_type="MinimalComponent")
        source_stack.add_component(label="root_b", component_type="MinimalComponent")

        filepath = self._tmp_json()
        source_stack.save(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        # -- Both roots from the source file become children of the target
        child_labels = sorted(c.label() for c in target_parent.children)
        self.assertEqual(child_labels, ["root_a", "root_b"])

    # --------------------------------------------------------------------------
    # Error / edge cases
    # --------------------------------------------------------------------------

    def test_import_subtree_nonexistent_file_is_noop(self):
        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        # -- Should not raise; just no-op
        dest_stack.import_subtree_under(
            parent=target_parent,
            filepath=self._tmp_json("does_not_exist.json"),
        )

        self.assertEqual(len(target_parent.children), 0)

    def test_import_subtree_empty_filepath_is_noop(self):
        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath="")

        self.assertEqual(len(target_parent.children), 0)

    # --------------------------------------------------------------------------
    # Component.import_subtree (convenience wrapper)
    # --------------------------------------------------------------------------

    def test_component_import_subtree_adds_loaded_component_as_child(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        # -- Use the Component.import_subtree convenience wrapper
        target_parent.import_subtree(filepath)

        self.assertEqual(len(target_parent.children), 1)
        self.assertEqual(target_parent.children[0].label(), "source_component")

    # --------------------------------------------------------------------------
    # Round-trip
    # --------------------------------------------------------------------------

    def test_round_trip_preserves_options_inputs_and_hierarchy(self):
        source_stack = self._make_stack()
        root = source_stack.add_component(
            label="root",
            component_type="ComponentWithOption",
        )
        root.option("test_option").set("root_value")

        child = source_stack.add_component(
            label="child",
            component_type="ComponentWithOption",
            parent=root,
        )
        child.option("test_option").set("child_value")

        filepath = self._tmp_json()
        root.save_settings(filepath)

        dest_stack = self._make_stack()
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )
        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        imported_root = target_parent.children[0]
        imported_child = imported_root.children[0]

        self.assertEqual(imported_root.option("test_option").get(), "root_value")
        self.assertEqual(imported_child.option("test_option").get(), "child_value")

    # --------------------------------------------------------------------------
    # Label collision warning
    # --------------------------------------------------------------------------

    def test_import_subtree_warns_on_label_collision(self):
        # -- Source component with a label
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="duplicate_label",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        # -- Destination already has a component with the same label
        dest_stack = self._make_stack()
        dest_stack.add_component(
            label="duplicate_label",
            component_type="MinimalComponent",
        )
        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        # -- Capture the log to verify a warning was given.
        with self.assertLogs("xstack.stack", level="WARNING") as captured:
            dest_stack.import_subtree_under(
                parent=target_parent,
                filepath=filepath,
            )

        output = "\n".join(captured.output)
        self.assertIn("duplicate_label", output)
        self.assertIn("label collision", output.lower())

        # -- The import should still have happened despite the warning.
        self.assertEqual(len(target_parent.children), 1)

    # --------------------------------------------------------------------------
    # Subtree-load doesn't disturb existing components
    # --------------------------------------------------------------------------

    def test_import_subtree_does_not_modify_existing_components(self):
        source_stack = self._make_stack()
        source_component = source_stack.add_component(
            label="source_component",
            component_type="MinimalComponent",
        )

        filepath = self._tmp_json()
        source_component.save_settings(filepath)

        dest_stack = self._make_stack()
        existing_component = dest_stack.add_component(
            label="existing",
            component_type="MinimalComponent",
        )
        existing_uuid = existing_component.uuid()

        target_parent = dest_stack.add_component(
            label="target_parent",
            component_type="MinimalComponent",
        )

        dest_stack.import_subtree_under(parent=target_parent, filepath=filepath)

        # -- existing_component should still be in the stack with the same UUID
        self.assertIn(existing_component, dest_stack.root_components)
        self.assertEqual(existing_component.uuid(), existing_uuid)


# ------------------------------------------------------------------------------
class TestBuildResults(unittest.TestCase):
    """
    Tests for how builds report failure, disabled hierarchies and nested builds.
    """

    def _make_stack(self):
        stack = xstack.Stack(component_paths=[COMPONENT_PATH])
        self.finished = []
        self.failed = []
        self.started = []
        stack.build_finished.connect(self.finished.append)
        stack.build_failed.connect(lambda component, details: self.failed.append(component))
        stack.build_started.connect(lambda: self.started.append(True))
        return stack

    def test_run_returning_false_fails_the_build(self):
        stack = self._make_stack()
        component = stack.add_component(label="false", component_type="ReturnsFalseComponent")
        after = stack.add_component(label="after", component_type="MinimalComponent")

        self.assertFalse(stack.build())
        self.assertEqual(component.status(), xstack.constants.Status.Failed)
        self.assertEqual(after.status(), xstack.constants.Status.NotExecuted)
        self.assertTrue(component.last_error())
        self.assertEqual(self.finished, [False])
        self.assertEqual(self.failed, [component])

    def test_exception_reports_the_traceback(self):
        stack = self._make_stack()
        component = stack.add_component(label="fail", component_type="FailingComponent")
        details = []
        stack.build_failed.connect(lambda failed, text: details.append(text))

        self.assertFalse(stack.build())
        self.assertIn("Enforced Failure", details[0])
        self.assertEqual(self.failed, [component])

    def test_invalid_component_reports_failure(self):
        stack = self._make_stack()
        component = stack.add_component(label="invalid", component_type="InvalidComponent")

        self.assertFalse(stack.build())
        self.assertEqual(self.finished, [False])
        self.assertEqual(self.failed, [component])

    def test_success_emits_finished(self):
        stack = self._make_stack()
        stack.add_component(label="ok", component_type="MinimalComponent")

        self.assertTrue(stack.build())
        self.assertEqual(self.finished, [True])
        self.assertEqual(self.failed, [])

    def test_disabled_component_skips_its_children(self):
        stack = self._make_stack()
        parent = stack.add_component(label="parent", component_type="MinimalComponent")
        child = stack.add_component(label="child", component_type="MinimalComponent", parent=parent)
        grandchild = stack.add_component(label="grandchild", component_type="MinimalComponent", parent=child)
        parent.set_enabled(False)

        self.assertTrue(stack.build())
        self.assertEqual(child.status(), xstack.constants.Status.NotExecuted)
        self.assertEqual(grandchild.status(), xstack.constants.Status.NotExecuted)

    def test_nested_build_leaves_the_outer_build_alone(self):
        stack = self._make_stack()
        first = stack.add_component(label="first", component_type="MinimalComponent")
        runner = stack.add_component(
            label="runner",
            component_type="NestedBuildComponent",
            options={"Target": "block"},
        )
        block = stack.add_component(label="block", component_type="MinimalComponent")
        stack.add_component(label="inner", component_type="MinimalComponent", parent=block)

        self.assertTrue(stack.build(build_up_to=runner))

        # -- The nested build did not reset the status of the outer components,
        # -- or emit the build signals part way through
        self.assertEqual(first.status(), xstack.constants.Status.Success)
        self.assertEqual(self.started, [True])
        self.assertEqual(self.finished, [True])

    def test_nested_failure_fails_the_outer_build(self):
        stack = self._make_stack()
        runner = stack.add_component(
            label="runner",
            component_type="NestedBuildComponent",
            options={"Target": "block"},
        )
        after = stack.add_component(label="after", component_type="MinimalComponent")
        block = stack.add_component(label="block", component_type="MinimalComponent")
        inner = stack.add_component(label="inner", component_type="ReturnsFalseComponent", parent=block)

        self.assertFalse(stack.build())
        self.assertEqual(runner.status(), xstack.constants.Status.Failed)
        self.assertEqual(after.status(), xstack.constants.Status.NotExecuted)

        # -- The component which actually failed is the one reported
        self.assertEqual(self.failed, [inner])
        self.assertEqual(self.finished, [False])

    def test_recursive_nested_builds_are_refused(self):
        stack = self._make_stack()
        block_a = stack.add_component(label="a", component_type="MinimalComponent")
        stack.add_component(label="run b", component_type="NestedBuildComponent", options={"Target": "b"}, parent=block_a)
        block_b = stack.add_component(label="b", component_type="MinimalComponent")
        stack.add_component(label="run a", component_type="NestedBuildComponent", options={"Target": "a"}, parent=block_b)

        self.assertFalse(stack.build(build_below=block_a))
        self.assertEqual(self.finished, [False])


# ------------------------------------------------------------------------------
class TestLoading(unittest.TestCase):
    """
    Tests for loading data with missing component types, versions and unknown keys.
    """

    def _make_stack(self):
        return xstack.Stack(component_paths=[COMPONENT_PATH])

    def test_missing_component_keeps_its_data(self):
        stack = self._make_stack()
        root = stack.add_component(label="root", component_type="ComponentWithOption")
        root.option("test_option").set("kept")
        root.set_enabled(False)
        stack.add_component(label="child", component_type="MinimalComponent", parent=root)

        data = stack.serialise()
        data["tree"][0]["component_type"] = "Not A Real Component"
        data["tree"][0]["additional_data"] = {"anything": [1, 2]}
        original = json.dumps(data)

        loaded = self._make_stack()
        with self.assertLogs("xstack.stack", level="WARNING"):
            loaded.deserialise(json.loads(original))

        placeholder = loaded.root_components[0]
        self.assertIsInstance(placeholder, xstack.MissingComponent)
        self.assertEqual(placeholder.missing_identifier, "Not A Real Component")
        self.assertEqual(placeholder.children[0].label(), "child")

        # -- Saving it again loses nothing
        self.assertEqual(json.dumps(loaded.serialise()), original)

    def test_missing_component_does_not_build(self):
        stack = self._make_stack()
        stack.add_component(label="root", component_type="MinimalComponent")
        data = stack.serialise()
        data["tree"][0]["component_type"] = "Not A Real Component"

        loaded = self._make_stack()
        loaded.deserialise(data)

        with self.assertLogs("xstack.component", level="WARNING") as captured:
            self.assertFalse(loaded.build())

        self.assertIn("Not A Real Component", "\n".join(captured.output))

    def test_switching_a_missing_component_keeps_matching_values(self):
        stack = self._make_stack()
        stack.add_component(label="root", component_type="ComponentWithOption", options={"test_option": "kept"})
        data = stack.serialise()
        data["tree"][0]["component_type"] = "Not A Real Component"

        loaded = self._make_stack()
        loaded.deserialise(data)
        replaced = loaded.replace_component(loaded.root_components[0], "ComponentWithOption")

        self.assertEqual(replaced.option("test_option").get(), "kept")

    def test_older_data_is_migrated(self):
        data = dict(
            label="stack",
            format="galaxy",
            tree=[
                dict(
                    component_type="MigratingComponent",
                    label="migrating",
                    uuid="abc",
                    inputs={},
                    options={"Old Name": "value"},
                    children=[],
                ),
            ],
        )

        stack = self._make_stack()
        stack.deserialise(data)

        component = stack.root_components[0]
        self.assertEqual(component.option("New Name").get(), "value")
        self.assertEqual(component.serialise()["version"], 2)

    def test_unknown_option_is_reported(self):
        stack = self._make_stack()

        with self.assertLogs("xstack.stack", level="WARNING") as captured:
            stack.add_component(label="opt", component_type="ComponentWithOption", options={"unknown": 1})

        self.assertIn("unknown", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()