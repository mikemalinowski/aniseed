"""
The TransformMixer - a pose system which blends sets of transforms (poses)
onto deformer transforms, much like a blendshape does for vertices.
"""
import functools

import mref


class TransformMixer:
    """
    Allows for transforms to be interacted with in the same way that blendshapes
    can be interacted with.

    The mixer node holds a float attribute per pose (the pose weight). Each
    deformer has one target transform per pose, and the deformer's
    translate, rotate and scale are the sum of every target's local values
    multiplied by the weight of that target's pose.

    Adding a deformer generates a target for each existing pose, and adding
    a pose generates a target for each existing deformer.

    Args:
        node: An existing mixer node to bind to. If not given a new mixer
            node is created.
        parent: The parent for the new mixer node (only used when no node
            is given)
    """

    def __init__(self, node=None, parent=None):

        if not node:
            node = self.create_node(parent=parent)
        self.node = mref.get(node)

        self.target_lookup = dict()

        # -- Context-manager state: when used as ``with mixer:``, the
        # -- viewport refresh and undo recording are suspended for the
        # -- duration of the block. The refcount lets nested ``with``
        # -- blocks behave correctly — only the outermost enter/exit
        # -- actually flips the Maya state.
        self._suspend_depth = 0
        self._previous_undo_state = None

        # -- Cached output of get_target_mapping(). Updated or invalidated
        # -- whenever poses/deformers/targets change.
        self._target_mapping_cache = None

    def __enter__(self):
        """
        Suspends viewport refresh and undo recording while inside the
        ``with`` block. Useful for any batch operation that creates or
        mutates many nodes — ``deserialise`` uses this internally, and
        external callers can wrap their own ``add_pose`` /
        ``add_deformer`` loops the same way::

            with mixer:
                for name in pose_names:
                    mixer.add_pose(name)
        """
        if self._suspend_depth == 0:
            self._previous_undo_state = mref.undoInfo(
                query=True,
                stateWithoutFlush=True,
            )
            mref.refresh(suspend=True)
            mref.undoInfo(stateWithoutFlush=False)
        self._suspend_depth += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Restores the viewport refresh and undo state when the outermost
        ``with`` block exits. Exceptions are never suppressed.
        """
        self._suspend_depth -= 1
        if self._suspend_depth == 0:
            mref.undoInfo(stateWithoutFlush=self._previous_undo_state)
            mref.refresh(suspend=False)
        # -- Don't suppress exceptions — let any error propagate.
        return False

    def add_deformer(self, name):
        """
        Creates a deformer (a deformer_<name> transform beneath a
        deformerspace_<name> parent) and a target for it for every existing
        pose.

        Args:
            name: The name of the deformer

        Returns:
            The deformer transform (mref item)
        """
        deformer_parent = mref.create("transform", name=f"deformerspace_{name}", parent=self.deformer_root())

        new_deformer = mref.create("transform", name=f"deformer_{name}", parent=deformer_parent)
        new_deformer.add_attribute(
            "deformer_name",
            attribute_type="string",
            value=name,
        )

        new_deformer.attr("message").connect_next(self.node.attr("deformers"))

        new_entries = {}
        for pose in self.poses():
            target = self.create_target(new_deformer, pose)
            pose_name = pose.attr("pose_name").get()
            new_entries[f"{pose_name}--{name}"] = target

        # -- Incrementally update the target mapping cache instead of
        # -- invalidating it. Avoids the O(N²) rebuild cost when many
        # -- deformers / poses are added in sequence.
        if self._target_mapping_cache is not None:
            self._target_mapping_cache.update(new_entries)

        # -- The new deformer name may have been queried before it was
        # -- added (and cached as "not found"), so clear that.
        self.get_deformer.cache_clear()

        return new_deformer

    def pose_attributes(self):
        """
        Returns the float user defined attributes of the mixer node - which
        are the pose weight attributes.

        Returns:
            List of attributes (mref items)
        """
        results = []
        for attribute in self.node.attributes(ud=True):
            if attribute.get_type() == "float":
                results.append(attribute)
        return results

    def add_pose(self, name):
        """
        Creates a pose: a keyable <name> weight attribute and a
        show_<name>_targets visibility attribute on the mixer node, a
        pose_<name> transform, and a target for every existing deformer.

        Args:
            name: The name of the pose

        Returns:
            The pose transform (mref item)
        """
        self.node.add_attribute(
            name,
            attribute_type="float",
            keyable=True,
            value=0,
        )

        visibility_label = f"show_{name}_targets"
        if not self.node.has_attribute(visibility_label):
            self.node.add_attribute(
                visibility_label,
                attribute_type="bool",
                keyable=True,
                value=False,
            )
        new_pose = mref.create("transform", name=f"pose_{name}", parent=self.pose_root())
        new_pose.add_attribute(
            "pose_name",
            attribute_type="string",
            value=name,
        )

        new_pose.add_attribute(
            "targets",
            attribute_type="message",
            value=None,
            multi=True,
        )

        new_pose.attr("message").connect_next(self.node.attr("poses"))

        new_entries = {}
        for deformer in self.deformers():
            target = self.create_target(deformer, new_pose)
            self.node.attr(visibility_label).connect(target.attr("visibility"))
            deformer_name = deformer.attr("deformer_name").get()
            new_entries[f"{name}--{deformer_name}"] = target

        # -- Incrementally update the target mapping cache instead of
        # -- invalidating it. Avoids the O(N²) rebuild cost when many
        # -- deformers / poses are added in sequence.
        if self._target_mapping_cache is not None:
            self._target_mapping_cache.update(new_entries)

        # -- The new pose name may have been queried before it was
        # -- added (and cached as "not found"), so clear that.
        self.get_pose.cache_clear()

        return new_pose

    def create_target(self, deformer, pose):
        """
        Creates the target transform for the given deformer and pose, at
        the deformer's current world transform and with a locator shape,
        and wires its local translate, rotate and scale (as an offset from
        1) multiplied by the pose weight into the deformer.

        Args:
            deformer: The deformer transform (mref item)
            pose: The pose transform (mref item)

        Returns:
            The target transform (mref item)
        """
        label = f"{deformer.name()}__{pose.name()}"

        target = mref.create("transform", name=f"target__{label}", parent=deformer.parent())
        target.set_matrix(deformer.get_matrix(space="world"), space="world")

        # -- Add a built-in locator shape rather than loading a curve
        # -- from disk. The locator is rendered natively by Maya, has
        # -- localScale / localPosition for sizing, and is the standard
        # -- visual idiom for "transform in space" — much faster than
        # -- the curve-create-then-delete-temp-transform cycle.
        mref.create("locator", parent=target)

        target.add_attribute(
            "deformer_name",
            attribute_type="string",
            value=deformer.attr("deformer_name").get()
        )
        target.add_attribute(
            "pose_name",
            attribute_type="string",
            value=pose.attr("pose_name").get(),
        )
        target.attr("message").connect_next(pose.attr("targets"))
        blend_translation = mref.create("multiplyDivide", name=f"blendtrans__{label}")
        blend_rotation = mref.create("multiplyDivide", name=f"blendtrot__{label}")
        blend_scale = mref.create("multiplyDivide", name=f"blendtscale__{label}")

        # -- Each deformer channel is driven by a plusMinusAverage which
        # -- sums all the targets. Reuse it if it already exists.
        try:
            translation_combiner = deformer.attr("translate").inputs()[0].node()
        except IndexError:
            translation_combiner = mref.create("plusMinusAverage", name=f"addtranslation_{label}")
            translation_combiner.attr("output3D").connect(deformer.attr("translate"))

        try:
            rotation_combiner = deformer.attr("rotate").inputs()[0].node()
        except IndexError:
            rotation_combiner = mref.create("plusMinusAverage", name=f"addrotate_{label}")
            rotation_combiner.attr("output3D").connect(deformer.attr("rotate"))

        # -- The scale sum is offset by one (scaleFromZero) before reaching
        # -- the deformer, so the combiner is two nodes upstream
        try:
            scale_combiner = deformer.attr("scale").inputs()[0].node().inputs()[0]
        except IndexError:
            scale_combiner = mref.create("plusMinusAverage", name=f"addscale_{label}")
            add_one = mref.create("plusMinusAverage", name=f"scaleFromZero_{label}")
            for axis in ["x", "y", "z"]:
                add_one.attr(f"input3D[0].input3D{axis}").set(1)
            scale_combiner.attr("output3D").connect_next(add_one.attr("input3D"))
            add_one.attr("output3D").connect(deformer.attr("scale"))

        target.attr("translate").connect(blend_translation.attr("input1"))
        target.attr("rotate").connect(blend_rotation.attr("input1"))

        # -- For the scale we need to add from zero rather than 1
        scale_from_zero = mref.create("plusMinusAverage", name=f"scaleFromZero_{label}")
        scale_from_zero.attr("operation").set(2)  # -- Subtract
        target.attr("scale").connect_next(scale_from_zero.attr("input3D"))
        scale_from_zero.attr("output3D").connect(blend_scale.attr("input1"))

        for axis in ["x", "y", "z"]:
            scale_from_zero.attr(f"input3D[1].input3D{axis}").set(1)

        for axis in ["X", "Y", "Z"]:
            driving_attribute = self.node.attr(pose.attr("pose_name").get())
            driving_attribute.connect(blend_translation.attr(f"input2{axis}"))
            driving_attribute.connect(blend_rotation.attr(f"input2{axis}"))
            driving_attribute.connect(blend_scale.attr(f"input2{axis}"))

        blend_translation.attr("output").connect_next(translation_combiner.attr("input3D"))
        blend_rotation.attr("output").connect_next(rotation_combiner.attr("input3D"))
        blend_scale.attr("output").connect_next(scale_combiner.attr("input3D"))

        return target

    def create_node(self, parent=None):
        """
        Creates a new mixer node (a transformMixer transform with deformers
        and poses message arrays, and deformerRoot and poseRoot children).

        Args:
            parent: Optional parent for the mixer node

        Returns:
            The mixer node (mref item)
        """
        node = mref.create("transform", name="transformMixer", parent=parent)
        node.add_attribute(
            "deformers",
            attribute_type="message",
            value=None,
            multi=True,
        )
        node.add_attribute(
            "poses",
            attribute_type="message",
            value=None,
            multi=True,
        )
        mref.create("transform", name="deformerRoot", parent=node)
        mref.create("transform", name="poseRoot", parent=node)

        return node

    def remove_deformer(self, deformer_name):
        """
        Deletes the deformer with the given name along with all of its
        targets.

        Args:
            deformer_name: The name of the deformer to remove
        """
        self.get_deformer(deformer_name).delete()

        for pose in self.poses():
            pose_name = pose.attr("pose_name").get()
            target = self.get_target(pose_name=pose_name, deformer_name=deformer_name)
            if target:
                target.delete()
            # -- Drop the matching entry from the cache incrementally.
            if self._target_mapping_cache is not None:
                self._target_mapping_cache.pop(f"{pose_name}--{deformer_name}", None)

        self.get_deformer.cache_clear()

    def remove_pose(self, pose_name):
        """
        Deletes the pose with the given name, all of its targets, and its
        weight and visibility attributes on the mixer node.

        Args:
            pose_name: The name of the pose to remove
        """
        for deformer in self.deformers():
            deformer_name = deformer.attr("deformer_name").get()
            target = self.get_target(
                pose_name=pose_name,
                deformer_name=deformer_name,
            )
            if target:
                target.delete()

        self.get_pose(pose_name).delete()

        # -- Remove the pose-weight float and the visibility toggle from
        # -- the mixer node so they aren't left as orphans on self.node
        # -- after the pose has gone. Mirrors the attributes added by
        # -- add_pose.
        for attribute_name in (pose_name, f"show_{pose_name}_targets"):
            if self.node.has_attribute(attribute_name):
                self.node.attr(attribute_name).delete()

        # -- Drop every cache entry for this pose.
        if self._target_mapping_cache is not None:
            self._target_mapping_cache = {
                key: value
                for key, value in self._target_mapping_cache.items()
                if not key.startswith(f"{pose_name}--")
            }

        self.get_pose.cache_clear()

    def deformer_root(self):
        """
        Returns the deformerRoot transform beneath the mixer node.
        """
        return self.node.children(node_type="transform", name_match="deformerRoot")[0]

    def pose_root(self):
        """
        Returns the poseRoot transform beneath the mixer node.
        """
        return self.node.children(node_type="transform", name_match="poseRoot")[0]

    def poses(self):
        """
        Returns the pose transforms (mref items), in the order they were
        added.
        """
        return [n.node() for n in self.node.attr("poses").inputs()]

    def deformers(self):
        """
        Returns the deformer transforms (mref items), in the order they
        were added.
        """
        return [n.node() for n in self.node.attr("deformers").inputs()]

    @functools.lru_cache(maxsize=None)
    def get_pose(self, pose_name):
        """
        Returns the pose transform with the given name, or None if there is
        no such pose. Results are cached until the poses change.

        Args:
            pose_name: The name of the pose
        """
        for pose_node in self.poses():
            if pose_node.attr("pose_name").get() == pose_name:
                return pose_node
        return None

    @functools.lru_cache(maxsize=None)
    def get_deformer(self, deformer_name):
        """
        Returns the deformer transform with the given name, or None if
        there is no such deformer. Results are cached until the deformers
        change.

        Args:
            deformer_name: The name of the deformer
        """
        for deformer_node in self.deformers():
            if deformer_node.attr("deformer_name").get() == deformer_name:
                return deformer_node
        return None

    def get_target(self, pose_name, deformer_name):
        """
        Returns the target node for a given (pose, deformer) pair, or
        None if no such target exists. Backed by the cached
        ``get_target_mapping()`` lookup, so calls are O(1) after the
        first mapping build.

        Args:
            pose_name: The name of the pose
            deformer_name: The name of the deformer
        """
        return self.get_target_mapping().get(f"{pose_name}--{deformer_name}")

    def get_target_mapping(self):
        """
        Returns a dict mapping ``"{pose_name}--{deformer_name}"`` to
        the corresponding target node. The result is built from the scene
        on first access and cached on the mixer instance; add_deformer,
        add_pose, remove_deformer and remove_pose keep the cache up to date.
        """
        if self._target_mapping_cache is not None:
            return self._target_mapping_cache

        results = dict()
        for pose in self.poses():
            pose_name = pose.attr("pose_name").get()
            targets = [n.node() for n in pose.attr("targets").inputs()]

            for target in targets:
                results[f"{pose_name}--{target.attr('deformer_name').get()}"] = target

        self._target_mapping_cache = results
        return results

    def _invalidate_target_caches(self):
        """
        Clears the cached target mapping and per-name lookup caches, so
        subsequent get_target / get_pose / get_deformer calls re-query the
        scene. Use this if the mixer is changed outside of this instance.
        """
        self._target_mapping_cache = None
        self.get_pose.cache_clear()
        self.get_deformer.cache_clear()

    def serialise(self):
        """
        Returns the mixer as a dictionary, which can be rebuilt with
        deserialise. The deformer transforms are those of the deformerspace
        parents, and all matrices are local (object space)::

            {
                "deformers": [
                    {"name": "", "transform": [], "rotation_order": 0},
                ],
                "poses": [
                    {
                        "name": "",
                        "targets": [
                            {"name": "", "transform": []},
                        ]
                    }
                ]
            }
        """
        data = {
            "deformers": [],
            "poses": []
        }

        deformers = self.deformers()
        deformer_names = [
            deformer.attr("deformer_name").get()
            for deformer in deformers
        ]
        poses = self.poses()
        pose_names = [
            pose.attr("pose_name").get()
            for pose in poses
        ]
        target_data = self.get_target_mapping()

        for idx, deformer in enumerate(deformers):
            data["deformers"].append(
                {
                    "name": deformer_names[idx],
                    "transform": deformer.parent().get_matrix(),
                    "rotation_order": deformer.attr("rotateOrder").get(),
                }
            )

        for pose_idx, pose in enumerate(poses):
            pose_name = pose_names[pose_idx]
            pose_data = {
                "name": pose_name,
                "targets": [],
            }

            for deformer_idx, deformer in enumerate(deformers):
                deformer_name = deformer_names[deformer_idx]
                lookup_label = f"{pose_name}--{deformer_name}"
                target = target_data[lookup_label]
                pose_data["targets"].append(
                    {
                        "name": deformer_name,
                        "transform": target.get_matrix(),
                    }
                )
            data["poses"].append(pose_data)
        return data

    @classmethod
    def deserialise(cls, data, parent=None):
        """
        Creates a new mixer from data returned by serialise. The deformer
        and target transforms are applied as they are stored.

        Args:
            data: The serialised mixer data
            parent: Optional parent for the new mixer node

        Returns:
            The new TransformMixer
        """
        mixer = cls(parent=parent)

        with mixer:
            for deformer_data in data.get("deformers", list()):
                deformer = mixer.add_deformer(deformer_data["name"])
                deformer.parent().set_matrix(deformer_data["transform"])
                deformer.attr("rotateOrder").set(deformer_data["rotation_order"])

            for pose_data in data.get("poses", list()):
                mixer.add_pose(pose_data["name"])

                for target_data in pose_data["targets"]:
                    target = mixer.get_target(pose_data["name"], target_data["name"])
                    target.set_matrix(target_data["transform"])

        return mixer
