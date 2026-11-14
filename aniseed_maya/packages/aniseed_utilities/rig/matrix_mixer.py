"""
The MatrixMixer - a pose system which blends poses onto driven objects
through their offsetParentMatrix, much like a blendshape does for vertices.

There are only poses and driven objects: no deformers, targets or
constraint mapping.

Scene layout::

    matrixMixer (transform)              one per mixer, holds no shapes
        .driven[i]         <- driven object .message
        .drivenKey[i]      the name the driven object is stored under
        .drivenChain[i]    <- the driven object's multMatrix .message
        .poses[j]          <- pose node .message
        .<poseName>        keyable float, the pose weight

    pose_<name> (network)                one per pose
        .poseName          string
        .weight            <- matrixMixer.<poseName>
        .drivenMatrix[i]   matrix, sparse, the pose's delta for driven[i]

A pose matrix is a delta in the driven object's rest frame: at weight 1, on
its own, the pose moves the object as if the matrix were typed into its
channels. Identity matrices are not stored.

Each driven object's offsetParentMatrix is fed by one multMatrix whose
inputs, by logical index, are:

    [j]                  rotate/scale/shear of pose j, weighted (blendMatrix)
    [TRANSLATE_OFFSET+j] translation of pose j, weighted (blendMatrix)
    [REST_INDEX]         the object's rest local matrix, if it was folded
    [ORIGINAL_INDEX]     the original offsetParentMatrix input, or its value

Rotations and scales come first and translations last, so translations add
exactly and one pose's rotation never swings another pose's translation.
Contribution nodes only exist for the parts of a pose matrix which are not
identity.

The pose weight drives blendMatrix target weights, which are only soft
ranged, so weights above one and below zero extrapolate. (blendMatrix's
envelope is clamped to 0-1, so it is never used.)
"""
import re
import logging

import mref
from maya import cmds
from maya.api import OpenMaya as om

log = logging.getLogger(__name__)

# -- The bool attribute which marks a transform as a matrix mixer
MARKER_ATTRIBUTE = "matrixMixer"

# -- multMatrix input slots (see the module docstring)
TRANSLATE_OFFSET = 100000
REST_INDEX = 200000
ORIGINAL_INDEX = 200001

# -- Values within this of identity count as identity
TOLERANCE = 1e-6

TRANSLATE = "translate"
ROTATE_SCALE = "rotateScale"

# -- The channels folded into the chain (and zeroed) when an object is
# -- driven while away from rest, with their rest values
CHANNEL_REST_VALUES = {
    "translate": (0.0, 0.0, 0.0),
    "rotate": (0.0, 0.0, 0.0),
    "scale": (1.0, 1.0, 1.0),
    "shear": (0.0, 0.0, 0.0),
}

SHEAR_CHANNELS = ("shearXY", "shearXZ", "shearYZ")

# -- Pose names become attribute names on the mixer node
POSE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class MatrixMixer:
    """
    Blends poses (sets of matrices) onto driven objects through their
    offsetParentMatrix. See the module docstring for the scene layout.

    Args:
        node: An existing mixer node to bind to. If not given a new mixer
            node is created.
        parent: The parent for the new mixer node (only used when no node
            is given)
        namer: Optional callable taking a camel cased label (such as
            "BrowUpPose") and returning the name to give the node it labels,
            used for every node the mixer creates. If not given the nodes
            are given the mixer's own names (matrixMixer, pose_<name> etc).
    """

    def __init__(self, node=None, parent=None, namer=None):
        self.namer = namer

        if not node:
            node = self.create_node(parent=parent)
        self.node = mref.get(node)

        # -- Context-manager state, see __enter__
        self._suspend_depth = 0
        self._previous_undo_state = None

        # -- Cached lookups of the driven objects ((index, key, node, chain))
        # -- and poses ((index, node, name)), so building a large mixer does
        # -- not query the scene on every call. This instance's own changes
        # -- keep them up to date; refresh() clears them after the scene is
        # -- changed by anything else (such as an undo).
        self._driven_cache = None
        self._pose_cache = None

    def refresh(self) -> None:
        """
        Clears the cached driven object and pose lookups, so they are read
        from the scene again. Call this after the mixer has been changed by
        anything other than this instance, such as an undo.
        """
        self._driven_cache = None
        self._pose_cache = None

    # ----------------------------------------------------------------------
    # -- Context manager
    # ----------------------------------------------------------------------
    def __enter__(self):
        """
        Suspends viewport refresh and undo recording while inside the
        ``with`` block, for batch operations such as building from data.
        Nested blocks are allowed; only the outermost one flips the state.
        """
        if self._suspend_depth == 0:
            self._previous_undo_state = mref.undoInfo(query=True, stateWithoutFlush=True)
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

        return False

    # ----------------------------------------------------------------------
    # -- Naming
    # ----------------------------------------------------------------------
    def _name(self, default: str, label: str) -> str:
        """
        Returns the name for a new node: the namer's name for the label, or
        the default if there is no namer.
        """
        return self.namer(label) if self.namer else default

    @staticmethod
    def _camel(name: str) -> str:
        """
        Returns the name as a camel cased label part: anything which is not
        a letter or digit is dropped and the following letter capitalised
        ("CTL_brow_LF" becomes "CTLBrowLF").
        """
        parts = re.split(r"[^A-Za-z0-9]+", name)
        return "".join(
            part[:1].upper() + part[1:]
            for part in parts
            if part
        )

    @staticmethod
    def _safe(name: str) -> str:
        """
        Returns the name with anything which is not a letter, digit or
        underscore replaced by an underscore, for use in node names.
        """
        return re.sub(r"[^A-Za-z0-9_]", "_", name)

    # ----------------------------------------------------------------------
    # -- The mixer node
    # ----------------------------------------------------------------------
    def create_node(self, parent=None):
        """
        Creates a new mixer node: a transform with the driven and pose
        arrays, and its transform channels locked and hidden.

        Args:
            parent: Optional parent for the mixer node

        Returns:
            The mixer node (mref item)
        """
        node = mref.create("transform", name=self._name("matrixMixer", "Mixer"), parent=parent)

        node.add_attribute(MARKER_ATTRIBUTE, True, "bool")
        node.add_attribute("driven", None, "message", multi=True)
        node.add_attribute("drivenKey", None, "string", multi=True)
        node.add_attribute("drivenChain", None, "message", multi=True)
        node.add_attribute("poses", None, "message", multi=True)

        # -- The mixer only holds data, so its own transform is locked and
        # -- hidden, leaving the pose weights alone in the channel box
        for channel in ("translate", "rotate", "scale"):
            for axis in "XYZ":
                path = f"{node.full_name()}.{channel}{axis}"
                cmds.setAttr(path, keyable=False, channelBox=False)
                cmds.setAttr(path, lock=True)

        return node

    @staticmethod
    def is_mixer(node) -> bool:
        """
        Returns True if the given node is a matrix mixer node.
        """
        return bool(node) and mref.objExists(str(node)) and mref.get(node).has_attribute(MARKER_ATTRIBUTE)

    # ----------------------------------------------------------------------
    # -- Driven objects
    # ----------------------------------------------------------------------
    def _driven_lookup(self) -> list:
        """
        Returns the cached (index, key, node, chain) of every driven object,
        reading them from the scene if they are not cached.
        """
        if self._driven_cache is not None:
            return self._driven_cache

        results = []
        mixer = self.node.full_name()

        for index in cmds.getAttr(f"{mixer}.driven", multiIndices=True) or list():
            sources = cmds.listConnections(f"{mixer}.driven[{index}]", source=True, destination=False)
            if not sources:
                continue

            key = cmds.getAttr(f"{mixer}.drivenKey[{index}]") or ""
            chains = cmds.listConnections(f"{mixer}.drivenChain[{index}]", source=True, destination=False)
            results.append((index, key, mref.get(sources[0]), mref.get(chains[0]) if chains else None))

        self._driven_cache = results
        return results

    def driven_entries(self) -> list:
        """
        Returns (index, key, node) for every driven object, in index order.
        """
        return [
            (index, key, node)
            for index, key, node, _ in self._driven_lookup()
        ]

    def driven(self) -> list:
        """
        Returns the driven objects (mref items), in index order.
        """
        return [
            node
            for _, _, node in self.driven_entries()
        ]

    def driven_keys(self) -> list:
        """
        Returns the keys the driven objects are stored under, in index order.
        """
        return [
            key
            for _, key, _ in self.driven_entries()
        ]

    def driven_index(self, driven) -> int | None:
        """
        Returns the index of a driven object, or None if it is not driven by
        this mixer.

        Args:
            driven: The driven object's index, key or node
        """
        entries = self.driven_entries()

        if isinstance(driven, int):
            return driven if any(index == driven for index, _, _ in entries) else None

        for index, key, _ in entries:
            if key == str(driven):
                return index

        if not mref.objExists(str(driven)):
            return None

        node = mref.get(driven)
        for index, _, driven_node in entries:
            if driven_node == node:
                return index

        return None

    def driven_node(self, driven):
        """
        Returns the driven object (mref item) for an index, key or node, or
        None if it is not driven by this mixer.
        """
        index = self.driven_index(driven)
        if index is None:
            return None

        for entry_index, _, node in self.driven_entries():
            if entry_index == index:
                return node

        return None

    def driven_key(self, driven) -> str:
        """
        Returns the key a driven object is stored under.
        """
        index = self._require_driven(driven)
        for entry_index, key, _, _ in self._driven_lookup():
            if entry_index == index:
                return key
        return ""

    def chain(self, driven):
        """
        Returns the multMatrix feeding the driven object's
        offsetParentMatrix (mref item).
        """
        index = self._require_driven(driven)
        for entry_index, _, _, chain in self._driven_lookup():
            if entry_index == index:
                return chain
        return None

    def add_driven(self, node, key: str = None) -> int:
        """
        Makes the mixer drive the node through its offsetParentMatrix.

        Any existing offsetParentMatrix input (or value) is kept at the end of
        the chain, so the mixer layers on top of it. If the node's channels
        are not at rest their local matrix is folded into the chain and the
        channels zeroed, so nothing moves and the poses pivot about the node.

        Args:
            node: The node to drive
            key: The name the node is stored under in the mixer data. If not
                given the node's name is used.

        Returns:
            The driven object's index

        Raises:
            ValueError: If the node is already driven, the key is taken, or
                the node is away from rest and cannot be folded
        """
        node = mref.get(node)
        key = key or node.name()

        if self.driven_index(node) is not None:
            raise ValueError(f"{node.name()} is already driven by {self.node.name()}")

        if key in self.driven_keys():
            raise ValueError(f"{self.node.name()} already has a driven object stored as {key!r}")

        local = om.MMatrix(node.attr("matrix").get())
        fold = not is_identity(local)

        if fold:
            problem = fold_problem(node)
            if problem:
                raise ValueError(f"{node.name()} is away from rest and cannot be folded: {problem}")

        mixer = self.node.full_name()
        indices = cmds.getAttr(f"{mixer}.driven", multiIndices=True) or list()
        index = max(indices) + 1 if indices else 0

        chain = mref.create(
            "multMatrix",
            name=self._name(f"matrixMixerChain_{self._safe(key)}", f"{self._camel(key)}MixerChain"),
        )
        chain_name = chain.full_name()
        opm = f"{node.full_name()}.offsetParentMatrix"

        sources = cmds.listConnections(opm, source=True, destination=False, plugs=True)
        if sources:
            cmds.connectAttr(sources[0], f"{chain_name}.matrixIn[{ORIGINAL_INDEX}]")
        else:
            cmds.setAttr(f"{chain_name}.matrixIn[{ORIGINAL_INDEX}]", cmds.getAttr(opm), type="matrix")

        if fold:
            cmds.setAttr(f"{chain_name}.matrixIn[{REST_INDEX}]", list(local), type="matrix")
            zero_channels(node)

        cmds.connectAttr(f"{chain_name}.matrixSum", opm, force=True)

        cmds.connectAttr(f"{node.full_name()}.message", f"{mixer}.driven[{index}]")
        cmds.setAttr(f"{mixer}.drivenKey[{index}]", key, type="string")
        cmds.connectAttr(f"{chain_name}.message", f"{mixer}.drivenChain[{index}]")

        self._driven_cache = None
        return index

    def remove_driven(self, driven) -> None:
        """
        Stops driving the object, removing its pose matrices and putting back
        its original offsetParentMatrix input (or value) and, if they were
        folded, its channels. Nothing moves when no pose is active.

        Args:
            driven: The driven object's index, key or node
        """
        index = self._require_driven(driven)
        node = self.driven_node(index)
        chain = self.chain(index)
        mixer = self.node.full_name()

        for pose in self.poses():
            pose_index = self.pose_index(pose)
            self._remove_contributions(pose_index, index)
            self._remove_pose_element(pose, index)

        if chain:
            chain_name = chain.full_name()
            chain_indices = cmds.getAttr(f"{chain_name}.matrixIn", multiIndices=True) or list()

            rest = None
            if REST_INDEX in chain_indices:
                rest = om.MMatrix(cmds.getAttr(f"{chain_name}.matrixIn[{REST_INDEX}]"))

            original_sources = cmds.listConnections(
                f"{chain_name}.matrixIn[{ORIGINAL_INDEX}]",
                source=True,
                destination=False,
                plugs=True,
            )
            original_value = cmds.getAttr(f"{chain_name}.matrixIn[{ORIGINAL_INDEX}]")

            if node:
                opm = f"{node.full_name()}.offsetParentMatrix"
                cmds.disconnectAttr(f"{chain_name}.matrixSum", opm)

                if original_sources:
                    cmds.connectAttr(original_sources[0], opm, force=True)
                else:
                    cmds.setAttr(opm, original_value, type="matrix")

                if rest is not None:
                    set_channels_from_matrix(node, rest)

        # -- The mixer's links are broken before the chain is deleted, so the
        # -- delete cannot spread to the mixer node (see safe_delete)
        for attribute_name in ("driven", "drivenKey", "drivenChain"):
            cmds.removeMultiInstance(f"{mixer}.{attribute_name}[{index}]", b=True)

        if chain:
            safe_delete(chain.full_name())

        self._driven_cache = None

    def _require_driven(self, driven) -> int:
        """
        Returns the index of a driven object, raising ValueError if it is
        not driven by this mixer.
        """
        index = self.driven_index(driven)
        if index is None:
            raise ValueError(f"{driven} is not driven by {self.node.name()}")
        return index

    # ----------------------------------------------------------------------
    # -- Poses
    # ----------------------------------------------------------------------
    def _pose_lookup(self) -> list:
        """
        Returns the cached (index, node, name) of every pose, reading them
        from the scene if they are not cached.
        """
        if self._pose_cache is not None:
            return self._pose_cache

        results = []
        mixer = self.node.full_name()

        for index in cmds.getAttr(f"{mixer}.poses", multiIndices=True) or list():
            sources = cmds.listConnections(f"{mixer}.poses[{index}]", source=True, destination=False)
            if sources:
                pose = mref.get(sources[0])
                results.append((index, pose, pose.attr("poseName").get()))

        self._pose_cache = results
        return results

    def poses(self) -> list:
        """
        Returns the pose nodes (mref items), in the order they were added.
        """
        return [
            pose
            for _, pose, _ in self._pose_lookup()
        ]

    def pose_names(self) -> list:
        """
        Returns the pose names, in the order they were added.
        """
        return [
            name
            for _, _, name in self._pose_lookup()
        ]

    def get_pose(self, pose):
        """
        Returns the pose node for a pose name (or node), or None if the mixer
        has no such pose.
        """
        for _, pose_node, name in self._pose_lookup():
            if name == str(pose) or pose_node == pose:
                return pose_node
        return None

    def pose_index(self, pose) -> int | None:
        """
        Returns the index of the pose (a name or node) in the mixer's poses
        array, or None if the mixer has no such pose.
        """
        for index, pose_node, name in self._pose_lookup():
            if name == str(pose) or pose_node == pose:
                return index
        return None

    def weight_attribute(self, pose_name: str):
        """
        Returns the pose's weight attribute on the mixer node (mref item).
        """
        return self.node.attr(pose_name)

    def add_pose(self, name: str):
        """
        Creates a pose: a keyable weight attribute on the mixer node and a
        pose node holding its matrices. The pose starts empty, so it moves
        nothing.

        Args:
            name: The name of the pose, which becomes an attribute name

        Returns:
            The pose node (mref item)

        Raises:
            ValueError: If the name is not a valid attribute name, or is
                already a pose or attribute of the mixer node
        """
        if not POSE_NAME_PATTERN.match(name):
            raise ValueError(
                f"{name!r} is not a valid pose name: use letters, digits and underscores, "
                f"not starting with a digit",
            )

        if self.get_pose(name):
            raise ValueError(f"{self.node.name()} already has a pose called {name}")

        if self.node.has_attribute(name):
            raise ValueError(f"{self.node.name()} already has an attribute called {name}")

        self.node.add_attribute(name, 0.0, "float", keyable=True)

        pose = mref.create(
            "network",
            name=self._name(f"pose_{name}", f"{self._camel(name)}Pose"),
        )
        pose.add_attribute("poseName", name, "string")
        pose.add_attribute("weight", 0.0, "float")
        pose.add_attribute("drivenMatrix", None, "matrix", multi=True)

        self.node.attr(name).connect(pose.attr("weight"))
        pose.attr("message").connect_next(self.node.attr("poses"))

        self._pose_cache = None
        return pose

    def remove_pose(self, pose_name: str) -> None:
        """
        Deletes the pose: its contribution nodes, its pose node and its
        weight attribute on the mixer node.

        Args:
            pose_name: The name of the pose to remove
        """
        pose = self._require_pose(pose_name)
        pose_index = self.pose_index(pose)

        for driven_index, _, _ in self.driven_entries():
            self._remove_contributions(pose_index, driven_index)

        cmds.removeMultiInstance(f"{self.node.full_name()}.poses[{pose_index}]", b=True)
        safe_delete(pose.full_name())

        if self.node.has_attribute(pose_name):
            self.node.attr(pose_name).delete()

        self._pose_cache = None

    def rename_pose(self, pose_name: str, new_name: str) -> None:
        """
        Renames a pose, its weight attribute and (when the mixer has no
        namer) its pose node. Connections to the weight are kept.

        Raises:
            ValueError: If the new name is invalid or already taken
        """
        pose = self._require_pose(pose_name)

        if not POSE_NAME_PATTERN.match(new_name):
            raise ValueError(f"{new_name!r} is not a valid pose name")

        if self.node.has_attribute(new_name) or self.get_pose(new_name):
            raise ValueError(f"{self.node.name()} already has a pose or attribute called {new_name}")

        cmds.renameAttr(f"{self.node.full_name()}.{pose_name}", new_name)
        pose.attr("poseName").set(new_name)
        pose.rename(self._name(f"pose_{new_name}", f"{self._camel(new_name)}Pose"))

        self._pose_cache = None

    def _require_pose(self, pose_name):
        """
        Returns the pose node, raising ValueError if there is no such pose.
        """
        pose = self.get_pose(pose_name)
        if not pose:
            raise ValueError(f"{self.node.name()} has no pose called {pose_name}")
        return pose

    # ----------------------------------------------------------------------
    # -- Pose matrices
    # ----------------------------------------------------------------------
    def pose_matrix(self, pose_name, driven) -> om.MMatrix:
        """
        Returns the pose's matrix for the driven object (identity if the pose
        does not move it).
        """
        pose = self._require_pose(pose_name)
        index = self._require_driven(driven)
        plug = f"{pose.full_name()}.drivenMatrix"

        if index not in (cmds.getAttr(plug, multiIndices=True) or list()):
            return om.MMatrix()

        return om.MMatrix(cmds.getAttr(f"{plug}[{index}]"))

    def pose_matrices(self, pose_name) -> dict:
        """
        Returns {driven index: matrix} for every driven object the pose
        moves.
        """
        pose = self._require_pose(pose_name)
        plug = f"{pose.full_name()}.drivenMatrix"
        driven_indices = [index for index, _, _ in self.driven_entries()]

        return {
            index: om.MMatrix(cmds.getAttr(f"{plug}[{index}]"))
            for index in cmds.getAttr(plug, multiIndices=True) or list()
            if index in driven_indices
        }

    def pose_driven(self, pose_name) -> list:
        """
        Returns the driven objects (mref items) the pose moves.
        """
        indices = self.pose_matrices(pose_name)
        return [
            node
            for index, _, node in self.driven_entries()
            if index in indices
        ]

    def set_pose_matrix(self, pose_name, driven, matrix) -> None:
        """
        Sets the pose's matrix for the driven object. This is the only way
        pose data is written: the contribution nodes are created, swapped
        or deleted to suit the matrix, and an identity matrix removes the
        entry altogether.

        Args:
            pose_name: The name of the pose
            driven: The driven object's index, key or node
            matrix: The matrix (anything om.MMatrix accepts)
        """
        pose = self._require_pose(pose_name)
        pose_index = self.pose_index(pose)
        index = self._require_driven(driven)
        matrix = om.MMatrix(matrix)

        has_rotate_scale, has_translate = matrix_parts(matrix)

        if not has_rotate_scale and not has_translate:
            self._remove_contributions(pose_index, index)
            self._remove_pose_element(pose, index)
            return

        plug = f"{pose.full_name()}.drivenMatrix[{index}]"
        cmds.setAttr(plug, list(matrix), type="matrix")
        self._alias_pose_element(pose, index)

        self._set_contribution(pose, pose_index, index, ROTATE_SCALE, has_rotate_scale)
        self._set_contribution(pose, pose_index, index, TRANSLATE, has_translate)

    def _contribution_slot(self, pose_index: int, driven_index: int, part: str) -> str:
        """
        Returns the multMatrix input plug a pose's contribution part feeds.
        """
        chain = self.chain(driven_index)
        slot = pose_index if part == ROTATE_SCALE else TRANSLATE_OFFSET + pose_index
        return f"{chain.full_name()}.matrixIn[{slot}]"

    def _set_contribution(self, pose, pose_index: int, driven_index: int, part: str, needed: bool) -> None:
        """
        Creates the blendMatrix for one part (ROTATE_SCALE or TRANSLATE) of
        a pose's contribution to a driven object if it is needed and missing,
        or deletes it if it exists and is not needed.
        """
        slot = self._contribution_slot(pose_index, driven_index, part)
        sources = cmds.listConnections(slot, source=True, destination=False)

        if not needed:
            # -- The element is removed (breaking the connection) before the
            # -- blendMatrix is deleted. Deleting a node which still feeds
            # -- another makes Maya delete that one too, which would take the
            # -- whole chain with it.
            if self._slot_exists(slot):
                cmds.removeMultiInstance(slot, b=True)
            if sources:
                safe_delete(sources[0])
            return

        if sources:
            return

        pose_label = self._camel(pose.attr("poseName").get())
        key = self.driven_key(driven_index)
        part_label = "Rotate" if part == ROTATE_SCALE else "Translate"

        blend = mref.create(
            "blendMatrix",
            name=self._name(
                f"matrixMixer{part_label}_{self._safe(pose.attr('poseName').get())}_{self._safe(key)}",
                f"{pose_label}{self._camel(key)}{part_label}Blend",
            ),
        )
        blend_name = blend.full_name()

        if part == ROTATE_SCALE:
            cmds.setAttr(f"{blend_name}.target[0].translateWeight", 0.0)
        else:
            cmds.setAttr(f"{blend_name}.target[0].rotateWeight", 0.0)
            cmds.setAttr(f"{blend_name}.target[0].scaleWeight", 0.0)
            cmds.setAttr(f"{blend_name}.target[0].shearWeight", 0.0)

        pose_name = pose.full_name()
        cmds.connectAttr(f"{pose_name}.drivenMatrix[{driven_index}]", f"{blend_name}.target[0].targetMatrix")
        cmds.connectAttr(f"{pose_name}.weight", f"{blend_name}.target[0].weight")
        cmds.connectAttr(f"{blend_name}.outputMatrix", slot, force=True)

    def _remove_contributions(self, pose_index: int, driven_index: int) -> None:
        """
        Deletes both contribution parts of a pose for a driven object.
        """
        if not self.chain(driven_index):
            return

        for part in (ROTATE_SCALE, TRANSLATE):
            self._set_contribution(None, pose_index, driven_index, part, needed=False)

    def _remove_pose_element(self, pose, driven_index: int) -> None:
        """
        Removes a pose's matrix element (and its alias) for a driven object.
        """
        plug = f"{pose.full_name()}.drivenMatrix[{driven_index}]"

        if driven_index not in (cmds.getAttr(f"{pose.full_name()}.drivenMatrix", multiIndices=True) or list()):
            return

        alias = cmds.aliasAttr(plug, query=True)
        if alias:
            cmds.aliasAttr(f"{pose.full_name()}.{alias}", remove=True)

        cmds.removeMultiInstance(plug, b=True)

    def _alias_pose_element(self, pose, driven_index: int) -> None:
        """
        Aliases a pose's matrix element to the driven object's name, so the
        Attribute Editor reads pose_smile.CTL_Lip_LF rather than
        drivenMatrix[7]. Aliases are cosmetic, so a name which cannot be used
        is skipped.
        """
        plug = f"{pose.full_name()}.drivenMatrix[{driven_index}]"

        if cmds.aliasAttr(plug, query=True):
            return

        node = self.driven_node(driven_index)
        alias = self._safe(node.name() if node else self.driven_key(driven_index))

        if not alias or alias[0].isdigit() or cmds.attributeQuery(alias, node=pose.full_name(), exists=True):
            return

        try:
            cmds.aliasAttr(alias, plug)

        except RuntimeError:
            pass

    @staticmethod
    def _slot_exists(slot: str) -> bool:
        """
        Returns True if the multi element plug exists.
        """
        array, index = slot.rsplit("[", 1)
        return int(index.rstrip("]")) in (cmds.getAttr(array, multiIndices=True) or list())

    # ----------------------------------------------------------------------
    # -- Evaluation queries (used by the editing tools)
    # ----------------------------------------------------------------------
    def chain_inputs(self, driven) -> list:
        """
        Returns (logical index, evaluated matrix) for every input of the
        driven object's chain, in multiplication order.
        """
        chain = self.chain(driven).full_name()
        return [
            (index, om.MMatrix(cmds.getAttr(f"{chain}.matrixIn[{index}]")))
            for index in sorted(cmds.getAttr(f"{chain}.matrixIn", multiIndices=True) or list())
        ]

    def rest_frame(self, driven) -> om.MMatrix:
        """
        Returns the world matrix of the driven object's rest frame (the space
        its pose matrices are in): its folded rest matrix, then its original
        offsetParentMatrix, then its parent.
        """
        node = self.driven_node(driven)
        frame = om.MMatrix()

        for index, matrix in self.chain_inputs(driven):
            if index >= REST_INDEX:
                frame *= matrix

        return frame * parent_world_matrix(node)

    # ----------------------------------------------------------------------
    # -- Persistence
    # ----------------------------------------------------------------------
    def serialise(self) -> dict:
        """
        Returns the mixer as a dictionary, which can be rebuilt with
        deserialise or applied with apply_data. Only the matrices which are
        not identity are stored, keyed by the driven objects' keys::

            {
                "version": 1,
                "driven": ["CTL_Brow_LF", ...],
                "poses": [
                    {"name": "browUp_LF", "matrices": {"CTL_Brow_LF": [16 floats]}},
                ],
            }
        """
        keys = {
            index: key
            for index, key, _ in self.driven_entries()
        }

        data = {
            "version": 1,
            "driven": list(keys.values()),
            "poses": [],
        }

        for pose_name in self.pose_names():
            data["poses"].append(
                {
                    "name": pose_name,
                    "matrices": {
                        keys[index]: list(matrix)
                        for index, matrix in self.pose_matrices(pose_name).items()
                    },
                },
            )

        return data

    def apply_data(self, data: dict) -> list:
        """
        Adds the poses in the data (those the mixer does not have yet) and
        sets their matrices for every driven object the mixer has. Matrices
        for driven objects the mixer does not have are skipped.

        Args:
            data: Data from serialise

        Returns:
            The keys which had matrices but are not driven by this mixer
        """
        keys = self.driven_keys()
        missing = []

        for pose_data in (data or dict()).get("poses", list()):
            pose_name = pose_data["name"]

            if not self.get_pose(pose_name):
                self.add_pose(pose_name)

            for key, matrix in pose_data.get("matrices", dict()).items():
                if key not in keys:
                    if key not in missing:
                        missing.append(key)
                    continue

                self.set_pose_matrix(pose_name, key, matrix)

        return missing

    @classmethod
    def deserialise(cls, data, parent=None, namer=None, resolve=None) -> "MatrixMixer":
        """
        Creates a new mixer from data returned by serialise. Each driven key
        is resolved to a node, and keys which cannot be resolved are skipped
        with a warning (their matrices are not applied).

        Args:
            data: The serialised mixer data
            parent: Optional parent for the new mixer node
            namer: Optional callable naming the mixer's nodes (see the
                class arguments)
            resolve: Optional callable turning a key into a node name. If
                not given the key is used as the node name.

        Returns:
            The new MatrixMixer
        """
        mixer = cls(parent=parent, namer=namer)

        with mixer:
            for key in (data or dict()).get("driven", list()):
                node_name = resolve(key) if resolve else key

                if not node_name or not mref.objExists(node_name):
                    log.warning(f"{mixer.node.name()} : {key!r} does not exist, so it is not driven")
                    continue

                mixer.add_driven(node_name, key=key)

            mixer.apply_data(data)

        return mixer


# --------------------------------------------------------------------------
# -- Node helpers
# --------------------------------------------------------------------------
def safe_delete(node_name: str) -> None:
    """
    Deletes a node after breaking all of its outgoing connections. Maya
    deletes the nodes downstream of a deleted node when it was their only
    input, which would otherwise take a driven object's chain (or worse)
    with it.
    """
    if not cmds.objExists(node_name):
        return

    connections = cmds.listConnections(node_name, source=False, destination=True, plugs=True, connections=True) or list()
    for source, destination in zip(connections[::2], connections[1::2]):
        try:
            cmds.disconnectAttr(source, destination)

        except RuntimeError:
            pass

    cmds.delete(node_name)


# --------------------------------------------------------------------------
# -- Matrix helpers
# --------------------------------------------------------------------------
def is_identity(matrix, tolerance: float = TOLERANCE) -> bool:
    """
    Returns True if the matrix is identity, within the tolerance.
    """
    return om.MMatrix(matrix).isEquivalent(om.MMatrix(), tolerance)


def matrix_parts(matrix, tolerance: float = TOLERANCE) -> tuple:
    """
    Returns (has rotate/scale/shear, has translation) for a matrix.
    """
    matrix = om.MMatrix(matrix)

    has_translate = any(
        abs(matrix.getElement(3, column)) > tolerance
        for column in range(3)
    )
    has_rotate_scale = any(
        abs(matrix.getElement(row, column) - (1.0 if row == column else 0.0)) > tolerance
        for row in range(3)
        for column in range(3)
    )

    return has_rotate_scale, has_translate


def parent_world_matrix(node) -> om.MMatrix:
    """
    Returns the world matrix of the node's parent (identity at the world
    root). The node's own parentMatrix attribute is not used, as it already
    includes the node's offsetParentMatrix.
    """
    parents = cmds.listRelatives(mref.get(node).full_name(), parent=True, fullPath=True)
    if not parents:
        return om.MMatrix()

    return om.MMatrix(cmds.getAttr(f"{parents[0]}.worldMatrix[0]"))


def channel_attributes(node) -> list:
    """
    Returns the paths of the node's translate, rotate, scale and shear
    channels (the individual axes).
    """
    name = mref.get(node).full_name()
    return [
        f"{name}.{channel}{axis}"
        for channel in ("translate", "rotate", "scale")
        for axis in "XYZ"
    ] + [
        f"{name}.{channel}"
        for channel in SHEAR_CHANNELS
    ]


def fold_problem(node) -> str:
    """
    Returns why the node's local matrix cannot be folded into the chain
    (and its channels zeroed), or an empty string if it can. Folding needs
    the channels to be free, and the local matrix to be identity once they
    are zeroed.
    """
    node = mref.get(node)
    name = node.full_name()

    for path in channel_attributes(node):
        if cmds.getAttr(path, lock=True):
            return f"{path.split('.')[-1]} is locked"

        if cmds.listConnections(path, source=True, destination=False):
            return f"{path.split('.')[-1]} is connected"

    for channel in ("translate", "rotate", "scale"):
        if cmds.listConnections(f"{name}.{channel}", source=True, destination=False):
            return f"{channel} is connected"

    for attribute_name in ("rotateAxis", "jointOrient"):
        if cmds.attributeQuery(attribute_name, node=name, exists=True):
            if any(abs(value) > TOLERANCE for value in cmds.getAttr(f"{name}.{attribute_name}")[0]):
                return f"it has a {attribute_name}"

    return ""


def zero_channels(node) -> None:
    """
    Sets the node's translate, rotate and shear to zero and its scale to
    one, skipping any channel which is locked or connected.
    """
    name = mref.get(node).full_name()

    for channel, values in CHANNEL_REST_VALUES.items():
        attributes = (
            [f"{name}.{shear}" for shear in SHEAR_CHANNELS]
            if channel == "shear"
            else [f"{name}.{channel}{axis}" for axis in "XYZ"]
        )

        for path, value in zip(attributes, values):
            if cmds.getAttr(path, lock=True):
                continue

            if cmds.listConnections(path, source=True, destination=False):
                continue

            cmds.setAttr(path, value)


def set_channels_from_matrix(node, matrix) -> None:
    """
    Sets the node's translate, rotate (in its rotate order), scale and shear
    to reproduce the given local matrix.
    """
    node = mref.get(node)
    name = node.full_name()
    transform = om.MTransformationMatrix(om.MMatrix(matrix))

    rotation = transform.rotation(asQuaternion=True).asEulerRotation()
    rotation.reorderIt(cmds.getAttr(f"{name}.rotateOrder"))

    values = {
        "translate": tuple(transform.translation(om.MSpace.kTransform)),
        "rotate": tuple(om.MAngle(value).asDegrees() for value in (rotation.x, rotation.y, rotation.z)),
        "scale": tuple(transform.scale(om.MSpace.kTransform)),
    }

    for channel, channel_values in values.items():
        for axis, value in zip("XYZ", channel_values):
            cmds.setAttr(f"{name}.{channel}{axis}", value)

    for shear, value in zip(SHEAR_CHANNELS, transform.shear(om.MSpace.kTransform)):
        cmds.setAttr(f"{name}.{shear}", value)


# --------------------------------------------------------------------------
# -- Data helpers
# --------------------------------------------------------------------------
def find_mixers() -> list:
    """
    Returns every matrix mixer node in the scene (mref items).
    """
    return list(mref.ls(f"*.{MARKER_ATTRIBUTE}", f"*:*.{MARKER_ATTRIBUTE}", objectsOnly=True) or list())


def merge_unbound(data: dict, previous: dict) -> dict:
    """
    Returns the data with the matrices of the previous data added for every
    driven key the data does not drive. Storing a mixer which was built
    while one of its driven objects was missing must not lose that object's
    poses. Poses which are no longer in the data are not brought back.

    Args:
        data: The data serialised from the mixer
        previous: The data stored before

    Returns:
        The merged data (a new dictionary)
    """
    merged = {
        "version": data.get("version", 1),
        "driven": list(data.get("driven", list())),
        "poses": [
            {
                "name": pose_data["name"],
                "matrices": dict(pose_data.get("matrices", dict())),
            }
            for pose_data in data.get("poses", list())
        ],
    }

    bound = set(merged["driven"])
    poses = {
        pose_data["name"]: pose_data
        for pose_data in merged["poses"]
    }

    for pose_data in (previous or dict()).get("poses", list()):
        target = poses.get(pose_data["name"])
        if not target:
            continue

        for key, matrix in pose_data.get("matrices", dict()).items():
            if key in bound:
                continue

            target["matrices"][key] = matrix
            if key not in merged["driven"]:
                merged["driven"].append(key)

    return merged
