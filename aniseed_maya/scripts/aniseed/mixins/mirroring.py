"""
MirrorMixin adds a "Mirror" action to a RigComponent via xstack's
``mixin_functions`` extension point.

The component is expected to declare a "Location" option whose value is
compared against ``self.config.left`` and ``self.config.right``. Only those
two values are mirrorable; any other value (middle, front, back) makes the
component non-mirrorable and hides the menu action.

Mirroring duplicates the component and all of its children, then mirrors
their transforms. It happens in this order:

    1. Plan: the original subtree is gathered, and each component's mirror
       items and parent item are recorded before anything changes. The
       label of every mirrored component is worked out up front.
    2. Create the mirrored components, parent before child. Each one has
       its data copied, search-and-replaced, internal addresses re-pointed
       at the other mirrored components and its Location switched, all
       BEFORE its on_enter_stack runs. It is then parented under its
       mirrored parent, and the mirrored parent item is selected, so
       anything on_enter_stack creates (e.g. a joint created from the
       selection) lands in the mirrored hierarchy.
    3. Once every mirrored component exists, the original items are
       mirrored onto the mirrored items in one pass, paired by position.

Compose alongside RigComponent:

    class Arm(aniseed.RigComponent, aniseed.mixins.MirrorMixin):

        def mirror_mixin_items_to_mirror(self):
            return self.input("Bones").get()

        def mirror_mixin_parent_item(self):
            return mref.get(self.input("Bones").get()[0]).parent().name()

A mirrorable component provides:

    mirror_mixin_items_to_mirror()  The nodes to mirror, in a stable order.
                                    The mirrored component must return its
                                    corresponding nodes in the same order.
    mirror_mixin_parent_item()      The node selected before the mirrored
                                    component's on_enter_stack runs, i.e.
                                    where any generated skeleton is
                                    parented. Return an empty string for
                                    none.

and may optionally re-implement:

    mirror_mixin_prepare(mirrored_from)      Called on the mirrored component
                                             after its data has been
                                             wrangled, before on_enter_stack.
    mirror_mixin_post_mirror(mirrored_from)  Called on the mirrored component
                                             once all the transforms have
                                             been mirrored.
    can_mirror()                             To add further preconditions.

In both hooks, self is the newly created mirrored component, and
mirrored_from is the original component it was mirrored from.

During a mirror, a mirrored component can use these helpers from its hooks:

    mirror_mixin_mirrored_name(name)       The name with the search and
                                           replace applied.
    mirror_mixin_mirrored_node(name)       The node which mirrors the given
                                           node (what it became earlier in
                                           this mirror, else the replaced
                                           name if it exists, else itself).
    mirror_mixin_counterparts_exist(s, t)  True when every mirrored node
                                           exists, differs from its original
                                           and is not mirrored by another
                                           component.
    mirror_mixin_mirrored_nodes()          Original node -> node it became,
                                           so far in this mirror.
    mirror_mixin_copy_nodes(nodes)         Copies user supplied nodes into
                                           the mirrored hierarchy.
"""
import re

import mref
import qtility
import scribble
import aniseed_toolkit
from maya import cmds
from xstack import address


class MirrorMixin:

    # -- Mirror plane for left<->right swaps. Class-level so a subclass can
    # -- override it if a rig ever needs a different reflection.
    MIRROR_PLANE = "YZ"

    # -- Scribble key used to remember the last-used search:replace expression
    # -- for each direction of mirroring
    _SCRIBBLE_KEY = "aniseed_mirror_expression"

    # -- Appended to a mirrored component's label when the search and replace does not
    # -- give it a label of its own
    _MIRRORED_LABEL_SUFFIX = " (Mirrored)"

    # ----------------------------------------------------------------------------------
    # xstack framework integration -- do not override in components.
    # ----------------------------------------------------------------------------------
    def mixin_functions(self):
        """
        Exposes the "Mirror" action when the component can be mirrored.
        """
        if self.can_mirror():
            return {"Mirror": self._invoke_mirror_from_ui}
        return {}

    # ----------------------------------------------------------------------------------
    # Public API. Override can_mirror to gate the menu dynamically.
    # ----------------------------------------------------------------------------------
    def can_mirror(self) -> bool:
        """
        True when the component's Location option is set to the rig config's
        left or right value. Override to add further preconditions (e.g. a
        required input must be populated).
        """
        location_option = self.option("Location")
        if location_option is None:
            return False
        return location_option.get() in (self.config.left, self.config.right)

    def mirror(self, search_for: str = None, replace_with: str = None):
        """
        Duplicates this component and all of its children onto the opposite
        side and mirrors their transforms across MIRROR_PLANE. See the module
        documentation for the order in which this happens.

        The scene changes are made in a single undo chunk. Note that undoing
        does not remove the mirrored components from the stack.

        Args:
            search_for: Regex applied to the mirrored components' labels, inputs and options.
                Defaults to the original location as a whole token (so "LF"
                matches "JNT_Arm_01_LF" and "Arm LF 01", but not "LFoot").
            replace_with: The replacement. Defaults to the target location.

        Returns:
            The mirrored version of this component, or None if this component is not on
            a mirrorable side.
        """
        target_location = self._mirror_target_location()
        if not target_location or not self.can_mirror():
            return None

        default_search, default_replace = self._default_mirror_expression()
        if search_for is None:
            search_for = default_search
        if replace_with is None:
            replace_with = default_replace

        expression = re.compile(search_for)

        with aniseed_toolkit.utils.UndoChunk("Mirror Component"):
            original_selection = cmds.ls(selection=True, long=True) or []
            try:
                return self._mirror_subtree(
                    expression=expression,
                    replace_with=replace_with,
                    original_location=self.option("Location").get(),
                    target_location=target_location,
                )
            finally:
                self._restore_selection(original_selection)

    # ----------------------------------------------------------------------------------
    # Declarative surface -- components override to describe their bones.
    # ----------------------------------------------------------------------------------
    def mirror_mixin_items_to_mirror(self) -> list:
        """
        Return the list of scene-node names representing this component's
        bones. These transforms will be reflected across the mirror plane
        onto the mirrored component's corresponding nodes using
        ``aniseed_toolkit.scene.mirror.mirror_transforms``.

        The mirrored component must return its corresponding nodes in the same order.

        Default: empty list (no scene-side mirroring).
        """
        return []

    def mirror_mixin_parent_item(self) -> str:
        """
        Return the name of the node to select before the mirrored component's
        on_enter_stack runs - typically the parent of the component's first
        joint, so a joint created from the selection is parented correctly.
        The mirrored equivalent of this node is selected for the mirrored component.

        Default: empty string (nothing is selected).
        """
        return ""

    def mirror_mixin_prepare(self, mirrored_from) -> None:
        """
        Called on the newly created mirrored component (self) after its data
        has been copied, search-and-replaced and its Location switched, but
        before its on_enter_stack runs. Use this to wrangle any further data,
        such as clearing an input so that on_enter_stack regenerates a
        skeleton.

        Args:
            mirrored_from: The original component this one was mirrored from
        """
        return None

    def mirror_mixin_post_mirror(self, mirrored_from) -> None:
        """
        Called on the newly created mirrored component (self) once every
        transform in the mirrored subtree has been mirrored.

        Args:
            mirrored_from: The original component this one was mirrored from
        """
        return None

    # ----------------------------------------------------------------------------------
    # Helpers for use from mirror_mixin_prepare / mirror_mixin_post_mirror.
    # They are only meaningful on a mirrored component during a mirror.
    # ----------------------------------------------------------------------------------
    def mirror_mixin_mirrored_name(self, name: str) -> str:
        """
        Returns the given name with the mirror's search and replace applied.
        Outside of a mirror the name is returned unchanged.
        """
        context = getattr(self, "_mirror_context", None)
        if not context or not name:
            return name
        return context["expression"].sub(context["replace_with"], name)

    def mirror_mixin_mirrored_node(self, name: str) -> str:
        """
        Returns the node which mirrors the given node: the node it became
        earlier in this mirror, else its search and replaced name if that
        exists, else the node itself if it exists (e.g. a middle spine joint).
        Returns an empty string if none of those exist.
        """
        if not name:
            return ""

        context = getattr(self, "_mirror_context", None) or dict()
        candidates = [
            context.get("node_map", dict()).get(name),
            self.mirror_mixin_mirrored_name(name),
            name,
        ]

        for candidate in candidates:
            if candidate and mref.objExists(candidate):
                return candidate

        return ""

    def mirror_mixin_counterparts_exist(
            self,
            original_nodes: list,
            mirrored_nodes: list = None,
    ) -> bool:
        """
        True when every mirrored node exists, differs from its original node,
        and is not already mirrored by another component - i.e. the other
        side already has its own nodes which nothing else drives (for
        instance the user built a symmetric skeleton) and they can be used as
        they are.

        Nodes which belong to another component (such as the result of an
        earlier mirror) are never shared, so mirroring the same component
        twice gives the second mirrored component nodes of its own.

        Args:
            original_nodes: The original component's nodes
            mirrored_nodes: The mirrored component's corresponding nodes.
                Defaults to the mirrored names of the original nodes.
        """
        original_nodes = [node for node in original_nodes or [] if node]

        if mirrored_nodes is None:
            mirrored_nodes = [self.mirror_mixin_mirrored_name(node) for node in original_nodes]
        mirrored_nodes = [node for node in mirrored_nodes if node]

        if not original_nodes or len(original_nodes) != len(mirrored_nodes):
            return False

        for original_node, mirrored_node in zip(original_nodes, mirrored_nodes):
            if mirrored_node == original_node or not mref.objExists(mirrored_node):
                return False

        claimed = set(mirrored_nodes)
        for other in self.stack.components():
            if other is self or not isinstance(other, MirrorMixin):
                continue

            if claimed & set(MirrorMixin._items_of(other)):
                return False

        return True

    def mirror_mixin_mirrored_nodes(self) -> dict:
        """
        Returns a mapping of each original node to the node it became, for the
        components mirrored so far in this mirror. Outside of a mirror this
        is empty.
        """
        context = getattr(self, "_mirror_context", None) or dict()
        return dict(context.get("node_map", dict()))

    def mirror_mixin_copy_nodes(self, nodes: list) -> list:
        """
        Copies the given nodes (without their children) for the mirrored component, in
        order. Each copy is parented under the copy of its parent if that
        parent is also in the list, otherwise under the mirrored equivalent
        of its parent. Each copy is given the mirrored name, made unique if
        it is taken. Shapes are kept, so guides keep their visuals. The
        mirror pass then moves the copies into place.

        Returns:
            The names of the copies, in the same order as the nodes
        """
        copies = dict()
        results = []

        for node in nodes:
            if not node or not mref.objExists(node):
                results.append("")
                continue

            copy_ = cmds.duplicate(node, renameChildren=True)[0]

            # -- Only the node itself is wanted, so remove any child
            # -- transforms (shapes are kept)
            child_transforms = cmds.listRelatives(
                copy_,
                children=True,
                type=["transform", "joint"],
                fullPath=True,
            ) or []
            if child_transforms:
                cmds.delete(child_transforms)

            parent = (cmds.listRelatives(node, parent=True) or [""])[0]
            new_parent = copies.get(parent) or self.mirror_mixin_mirrored_node(parent)

            current_parent = (cmds.listRelatives(copy_, parent=True) or [""])[0]
            if new_parent and new_parent != current_parent:
                copy_ = cmds.parent(copy_, new_parent)[0]
            elif not new_parent and current_parent:
                copy_ = cmds.parent(copy_, world=True)[0]

            name = self.mirror_mixin_mirrored_name(node)
            candidate = name
            counter = 1
            while mref.objExists(candidate):
                candidate = f"{name}{counter}"
                counter += 1
            copy_ = cmds.rename(copy_, candidate)

            copies[node] = copy_
            results.append(copy_)

        return results

    # ----------------------------------------------------------------------------------
    # UI entry point -- prompts the user for the search:replace expression,
    # then calls mirror() with the collected arguments. Wired up via
    # mixin_functions above.
    # ----------------------------------------------------------------------------------
    def _invoke_mirror_from_ui(self):
        original_location = self.option("Location").get()
        target_location = self._mirror_target_location()

        if not target_location:
            return None

        default_expression = ":".join(self._default_mirror_expression())

        # -- Remember the last expression for each direction separately, as
        # -- an LF to RT expression is no use when mirroring RT to LF
        user_data = scribble.get(self._SCRIBBLE_KEY)
        direction_key = f"{original_location}:{target_location}"
        prior = user_data.get(direction_key, default_expression)

        response = qtility.request.text(
            title="Mirror Component",
            message=(
                "Enter a search-and-replace expression to apply to the "
                "mirrored component's data.\n\n"
                "Format: search:replace  (the search is treated as a regex)\n\n"
                f"Default swaps the location token: \"{default_expression}\""
            ),
            text=prior,
        )

        if not response:
            return None

        if ":" not in response:
            qtility.request.message(
                title="Mirror Component",
                message="Could not parse the search:replace expression.",
            )
            return None

        search_for, replace_with = response.split(":", 1)

        try:
            re.compile(search_for)
        except re.error as error:
            qtility.request.message(
                title="Mirror Component",
                message=f"The search is not a valid regular expression: {error}",
            )
            return None

        # -- Remember for next time
        user_data[direction_key] = response
        user_data.save()

        return self.mirror(search_for=search_for, replace_with=replace_with)

    # ----------------------------------------------------------------------------------
    # Implementation
    # ----------------------------------------------------------------------------------
    def _mirror_target_location(self) -> str:
        """
        Returns the opposite location to this component's, or an empty string
        if this component is not on the left or the right.
        """
        location_option = self.option("Location")
        if location_option is None:
            return ""

        original_location = location_option.get()

        if original_location == self.config.left:
            return self.config.right

        if original_location == self.config.right:
            return self.config.left

        return ""

    def _default_mirror_expression(self) -> tuple:
        """
        Returns the default (search, replace) pair: the original location as a
        whole token (not touching any other letter or digit) and the target
        location.
        """
        original_location = self.option("Location").get()
        target_location = self._mirror_target_location()

        search_for = rf"(?<![A-Za-z0-9]){re.escape(original_location)}(?![A-Za-z0-9])"
        return search_for, target_location

    def _mirror_subtree(self, expression, replace_with, original_location, target_location):
        """
        Creates mirrored versions of this component and all of its descendants, then
        mirrors their transforms. Returns the mirrored version of this component.
        """
        stack = self.stack

        # -- 1. Plan. Gather the subtree (parents before children) and record
        # -- everything we need from the original before anything changes.
        originals = self._subtree(self)

        original_items = {
            original: self._items_of(original)
            for original in originals
        }

        parent_items = {
            original: self._parent_item_of(original)
            for original in originals
        }

        mirrored_labels = self._plan_mirrored_labels(originals, expression, replace_with)

        # -- Addresses in the mirrored components which point at a component in the
        # -- subtree should point at that component's mirrored component. The search and
        # -- replace may already have changed the label inside an address,
        # -- so map both the original and the replaced label.
        label_map = dict()
        for original in originals:
            label_map[original.label()] = mirrored_labels[original]
            label_map[expression.sub(replace_with, original.label())] = mirrored_labels[original]

        # -- 2. Create the mirrored components, parent before child
        mirrored_components = dict()
        node_map = dict()

        for original in originals:

            mirrored_component = stack.add_component(
                component_type=original.identifier,
                label=mirrored_labels[original],
                suppress_events=True,
            )

            # -- Copy the data, then wrangle it before on_enter_stack runs.
            # -- copy() and search_and_replace() both set the label, so the
            # -- planned label is applied afterwards.
            mirrored_component.copy(original)
            mirrored_component.search_and_replace(
                search_for=expression.pattern,
                replace_with=replace_with,
            )
            mirrored_component.set_label(mirrored_labels[original])

            self._retarget_addresses(mirrored_component, label_map)

            location_option = mirrored_component.option("Location")
            if location_option is not None and location_option.get(resolved=False) == original_location:
                location_option.set(target_location)

            if isinstance(mirrored_component, MirrorMixin):
                mirrored_component._mirror_context = dict(
                    expression=expression,
                    replace_with=replace_with,
                    node_map=node_map,
                )
                mirrored_component.mirror_mixin_prepare(original)

            # -- The mirrored version of the root goes alongside the original. Every other
            # -- mirrored component goes under the mirrored version of its parent.
            mirrored_parent = mirrored_components.get(original.parent, original.parent)
            mirrored_component.set_parent(parent=mirrored_parent)

            # -- Select the mirrored equivalent of the original's parent item so
            # -- anything created from the selection lands in the mirrored
            # -- hierarchy
            self._select_mirrored(parent_items[original], node_map, expression, replace_with)

            mirrored_component.on_enter_stack()

            stack.component_added.emit(mirrored_component)
            stack.changed.emit()

            mirrored_components[original] = mirrored_component

            # -- Record which node each original item became, so that the
            # -- children of this component can find their mirrored parent
            mirrored_items = self._items_of(mirrored_component)
            for original_item, mirrored_item in zip(original_items[original], mirrored_items):
                if original_item and mirrored_item:
                    node_map[original_item] = mirrored_item

        # -- 3. Mirror the transforms in a single pass, so that parents and
        # -- children are all resolved together
        transforms = []
        targets = []

        for original in originals:
            mirrored_items = self._items_of(mirrored_components[original])

            if len(mirrored_items) != len(original_items[original]):
                print(
                    f"Mirror : {mirrored_components[original].label()} has {len(mirrored_items)} items to "
                    f"mirror but {original.label()} has {len(original_items[original])}. "
                    f"Only the first {min(len(mirrored_items), len(original_items[original]))} "
                    f"are paired."
                )

            for original_item, mirrored_item in zip(original_items[original], mirrored_items):

                if not original_item or not mirrored_item:
                    continue

                if original_item == mirrored_item:
                    print(f"Mirror : {original_item} would be mirrored onto itself, skipping")
                    continue

                if not mref.objExists(original_item) or not mref.objExists(mirrored_item):
                    print(f"Mirror : cannot pair {original_item} with {mirrored_item}, skipping")
                    continue

                transforms.append(original_item)
                targets.append(mirrored_item)

        if transforms:
            aniseed_toolkit.scene.mirror.mirror_transforms(
                transforms=transforms,
                targets=targets,
                across=self.MIRROR_PLANE,
                behaviour=True,
            )

        for original in originals:
            mirrored_component = mirrored_components[original]
            if isinstance(mirrored_component, MirrorMixin):
                mirrored_component.mirror_mixin_post_mirror(original)

        # -- The context only applies during the mirror
        for mirrored_component in mirrored_components.values():
            if hasattr(mirrored_component, "_mirror_context"):
                del mirrored_component._mirror_context

        return mirrored_components[self]

    @staticmethod
    def _subtree(component) -> list:
        """
        Returns the component followed by all of its descendants, with every
        parent before its children.
        """
        result = [component]
        for child in list(component.children):
            result.extend(MirrorMixin._subtree(child))
        return result

    @staticmethod
    def _items_of(component) -> list:
        """
        Returns the mirror items of the component, or an empty list if it does
        not use this mixin.
        """
        if not isinstance(component, MirrorMixin):
            return []
        return list(component.mirror_mixin_items_to_mirror() or [])

    @staticmethod
    def _parent_item_of(component) -> str:
        """
        Returns the mirror parent item of the component, or an empty string if
        it does not use this mixin.
        """
        if not isinstance(component, MirrorMixin):
            return ""
        return component.mirror_mixin_parent_item() or ""

    def _plan_mirrored_labels(self, originals, expression, replace_with) -> dict:
        """
        Works out a unique label for the mirrored version of every original component. The
        search and replace is applied to the label. If that leaves it
        unchanged, or it is already taken, the mirrored suffix (and a counter
        if needed) is added.
        """
        taken = {component.label() for component in self.stack.components()}
        labels = dict()

        for original in originals:
            label = expression.sub(replace_with, original.label())

            if label == original.label() or label in taken:
                label += self._MIRRORED_LABEL_SUFFIX

            candidate = label
            counter = 2
            while candidate in taken:
                candidate = f"{label} {counter}"
                counter += 1

            taken.add(candidate)
            labels[original] = candidate

        return labels

    @classmethod
    def _retarget_addresses(cls, component, label_map) -> None:
        """
        Re-points any address in the component's inputs and options whose
        component label is in label_map.
        """
        for attribute in component.inputs() + component.options():
            value = attribute.get(resolved=False)
            retargeted = cls._retargeted_value(value, label_map)

            if retargeted != value:
                attribute.set(retargeted)

    @classmethod
    def _retargeted_value(cls, value, label_map):
        """
        Returns the value with any addresses re-pointed, looking inside
        lists, tuples and dictionaries.
        """
        if isinstance(value, str):
            if address.is_address(value):
                label = address.get_label(value)
                if label in label_map:
                    return f"[{label_map[label]}]" + value[len(label) + 2:]
            return value

        if isinstance(value, list):
            return [cls._retargeted_value(item, label_map) for item in value]

        if isinstance(value, tuple):
            return tuple(cls._retargeted_value(item, label_map) for item in value)

        if isinstance(value, dict):
            return {
                key: cls._retargeted_value(item, label_map)
                for key, item in value.items()
            }

        return value

    @staticmethod
    def _select_mirrored(parent_item, node_map, expression, replace_with) -> None:
        """
        Selects the mirrored equivalent of the given node: the node it became
        if it was mirrored as part of this operation, otherwise the search
        and replaced name if that exists, otherwise the node itself (e.g. a
        middle spine joint). Clears the selection if there is no node.
        """
        cmds.select(clear=True)

        if not parent_item:
            return

        candidates = [
            node_map.get(parent_item),
            expression.sub(replace_with, parent_item),
            parent_item,
        ]

        for candidate in candidates:
            if candidate and mref.objExists(candidate):
                cmds.select(candidate)
                return

    @staticmethod
    def _restore_selection(selection) -> None:
        """
        Restores the given selection, ignoring any nodes which no longer exist.
        """
        existing = [node for node in selection if mref.objExists(node)]
        if existing:
            cmds.select(existing)
        else:
            cmds.select(clear=True)
