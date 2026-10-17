import typing

import mref
from maya.api import OpenMaya as om
from maya import cmds


_SUPPORTED_SPACES = ("object", "world")

# -- Long channel names mapped to their cmds.transformLimits flag
_LIMIT_CHANNELS = {
    f"{long_name}{axis.upper()}": f"{long_name[0]}{axis}"
    for long_name in ("translate", "rotate", "scale")
    for axis in "xyz"
}


class Transform(mref.Trait):
    """
    Trait bound to any node with ``MFn.kTransform`` — transforms,
    joints, cluster handles, follicles, and anything else with a
    transformation. Sits above ``DagNode`` and ``DependencyNode`` in
    the resolution chain.

    Provides matrix get/set, translation/rotation/scale convenience
    accessors, an ``xform`` passthrough that auto-injects this node's
    full DAG path, and a ``match_to`` helper for snapping one transform
    to another.

    Space handling: methods that take a ``space`` argument accept either
    ``"object"`` (the node's local transform space) or ``"world"`` (the
    scene root coordinate system). Other Maya transformation spaces
    (``kPreTransform``, ``kPostTransform``, etc.) are not supported by
    ``cmds.xform`` and would require a different API path.
    """

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        Returns True if the given pointer is an MObject with the
        ``kTransform`` function set.
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kTransform)

    def get_matrix(self, space: str = "object") -> list[float]:
        """
        Returns this transform's matrix as a flat 4x4 list of 16 floats
        in column-major order.

        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        return list(
            cmds.xform(
                self.item.full_name(),
                query=True,
                matrix=True,
                **self._space_kwargs(space),
            )
        )

    def set_matrix(self, matrix: list[float], space: str = "object") -> None:
        """
        Sets this transform's matrix from a flat 4x4 list of 16 floats
        in column-major order.

        :param matrix: Flat 4x4 matrix as 16 floats, column-major.
        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        cmds.xform(
            self.item.full_name(),
            matrix=matrix,
            **self._space_kwargs(space),
        )

    def get_position(self, space: str = "object") -> list[float]:
        """
        Returns the translation as ``[x, y, z]``.

        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        return list(
            cmds.xform(
                self.item.full_name(),
                query=True,
                translation=True,
                **self._space_kwargs(space),
            )
        )

    def set_position(self, position: list[float], space: str = "object") -> None:
        """
        Sets the translation from ``[x, y, z]``.

        :param position: Translation values as ``[x, y, z]``.
        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        cmds.xform(
            self.item.full_name(),
            translation=position,
            **self._space_kwargs(space),
        )

    def get_rotation(self, space: str = "object") -> list[float]:
        """
        Returns the rotation as ``[x, y, z]`` Euler angles in degrees.

        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        return list(
            cmds.xform(
                self.item.full_name(),
                query=True,
                rotation=True,
                **self._space_kwargs(space),
            )
        )

    def set_rotation(self, rotation: list[float], space: str = "object") -> None:
        """
        Sets the rotation from ``[x, y, z]`` Euler angles in degrees.

        :param rotation: Euler angles in degrees as ``[x, y, z]``.
        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        cmds.xform(
            self.item.full_name(),
            rotation=rotation,
            **self._space_kwargs(space),
        )

    def get_scale(self, space: str = "object") -> list[float]:
        """
        Returns the scale as ``[x, y, z]``.

        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        return list(
            cmds.xform(
                self.item.full_name(),
                query=True,
                scale=True,
                **self._space_kwargs(space),
            )
        )

    def set_scale(self, scale: list[float], space: str = "object") -> None:
        """
        Sets the scale from ``[x, y, z]``.

        :param scale: Scale factors as ``[x, y, z]``.
        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        cmds.xform(
            self.item.full_name(),
            scale=scale,
            **self._space_kwargs(space),
        )

    def xform(self, **kwargs) -> typing.Any:
        """
        Calls ``cmds.xform`` against this transform, auto-injecting its
        full DAG path as the first positional argument. The return type
        depends on the kwargs — ``query=True`` calls return a list of
        floats; mutating calls return ``None``.
        """
        return cmds.xform(self.item.full_name(), **kwargs)

    def match_to(
        self,
        other: mref.ReferencedItem|str,
        space: str = "world",
    ) -> None:
        """
        Match this transform to another. By default the match is in
        worldspace, which snaps this node to the same position /
        orientation / scale as ``other`` regardless of either node's
        parent hierarchy. Pass ``space="object"`` for an object-space
        copy of ``other``'s matrix (useful when both nodes share the
        same parent).
        """
        other = mref.get(other)
        self.set_matrix(other.get_matrix(space=space), space=space)

    # ------------------------------------------------------------------
    # Offset parent matrix
    # ------------------------------------------------------------------

    def get_offset_parent_matrix(self) -> list[float]:
        """
        Returns the ``offsetParentMatrix`` as a flat list of 16 floats.
        This matrix sits between the parent and the local transform, so
        it can hold a rest pose while translate/rotate/scale stay zeroed.
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.offsetParentMatrix"))

    def set_offset_parent_matrix(self, matrix: list[float]) -> None:
        """
        Sets the ``offsetParentMatrix`` from a flat list of 16 floats.
        """
        cmds.setAttr(
            f"{self.item.full_name()}.offsetParentMatrix",
            list(matrix),
            type="matrix",
        )

    # ------------------------------------------------------------------
    # Pivots, rotate order and limits
    # ------------------------------------------------------------------

    def get_pivot(self, space: str = "object") -> list[float]:
        """
        Returns the rotate pivot position as ``[x, y, z]``.

        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        return list(
            cmds.xform(
                self.item.full_name(),
                query=True,
                rotatePivot=True,
                **self._space_kwargs(space),
            )
        )

    def set_pivot(self, position: list[float], space: str = "object") -> None:
        """
        Moves both the rotate and scale pivots to the given position,
        as pressing D / Insert and moving the pivot does. The node does
        not move.

        :param position: Pivot position as ``[x, y, z]``.
        :param space: Either ``"object"`` (default) or ``"world"``.
        """
        cmds.xform(
            self.item.full_name(),
            pivots=position,
            **self._space_kwargs(space),
        )

    def get_rotate_order(self) -> str:
        """
        Returns the rotate order as a lower-case string, e.g. ``"xyz"``.
        """
        return cmds.xform(self.item.full_name(), query=True, rotateOrder=True)

    def set_rotate_order(self, rotate_order: str, preserve: bool = True) -> None:
        """
        Sets the rotate order from a string such as ``"zxy"``.

        :param preserve: If True (default), the rotate values are changed
            so the node keeps its current orientation. If False, only the
            order changes and the node visibly rotates.
        """
        cmds.xform(
            self.item.full_name(),
            rotateOrder=rotate_order.lower(),
            preserve=preserve,
        )

    def get_limits(self, channel: str) -> list[float|None]:
        """
        Returns the ``[minimum, maximum]`` transform limits of a single
        channel, with None for a side that is not enabled.

        :param channel: A channel name such as ``"tx"``, ``"rotateY"``
            or ``"scaleZ"``. Rotation limits are in degrees.
        """
        flag = self._limit_flag(channel)
        name = self.item.full_name()

        values = cmds.transformLimits(name, query=True, **{flag: True})
        enabled = cmds.transformLimits(name, query=True, **{f"e{flag}": True})

        return [
            value if state else None
            for value, state in zip(values, enabled)
        ]

    def set_limits(
        self,
        channel: str,
        minimum: float|None = None,
        maximum: float|None = None,
    ) -> None:
        """
        Sets the transform limits of a single channel. A side given as
        None is disabled, so ``set_limits("ty")`` removes both limits.

        :param channel: A channel name such as ``"tx"``, ``"rotateY"``
            or ``"scaleZ"``. Rotation limits are in degrees.
        """
        flag = self._limit_flag(channel)
        name = self.item.full_name()

        # -- transformLimits always takes both values, so keep the current
        # -- value for any side we are disabling
        current = cmds.transformLimits(name, query=True, **{flag: True})
        values = (
            current[0] if minimum is None else minimum,
            current[1] if maximum is None else maximum,
        )

        cmds.transformLimits(
            name,
            **{
                flag: values,
                f"e{flag}": (minimum is not None, maximum is not None),
            }
        )

    # ------------------------------------------------------------------
    # Freezing and resetting
    # ------------------------------------------------------------------

    def freeze_transforms(
        self,
        translate: bool = True,
        rotate: bool = True,
        scale: bool = True,
    ) -> None:
        """
        Freezes the transforms (``makeIdentity -apply``) — bakes the
        current translate / rotate / scale into the node's children and
        geometry so the channels read zero (one for scale) without
        anything moving. On joints a frozen rotation moves into
        ``jointOrient``.
        """
        cmds.makeIdentity(
            self.item.full_name(),
            apply=True,
            translate=translate,
            rotate=rotate,
            scale=scale,
        )

    def reset_transforms(
        self,
        translate: bool = True,
        rotate: bool = True,
        scale: bool = True,
    ) -> None:
        """
        Resets translate and rotate to zero and scale to one
        (``makeIdentity`` without ``-apply``). Unlike
        ``freeze_transforms`` this moves the node back to its parent's
        origin.
        """
        cmds.makeIdentity(
            self.item.full_name(),
            apply=False,
            translate=translate,
            rotate=rotate,
            scale=scale,
        )

    # ------------------------------------------------------------------
    # Orientation helpers
    # ------------------------------------------------------------------

    def axis_vector(self, axis: str = "x", space: str = "world") -> list[float]:
        """
        Returns the normalised direction one of this node's local axes
        points in, as ``[x, y, z]``.

        :param axis: ``"x"``, ``"y"`` or ``"z"``, optionally prefixed
            with ``"-"`` for the negative direction.
        :param space: ``"world"`` (default) for the direction in world
            space, or ``"object"`` for the direction in the parent's space.
        """
        negate = axis.startswith("-")
        index = "xyz".find(axis.lstrip("-+").lower())
        if index < 0 or len(axis.lstrip("-+")) != 1:
            raise ValueError(f"Unsupported axis {axis!r}; expected x, y or z")

        matrix = self.get_matrix(space=space)
        vector = om.MVector(matrix[index * 4: index * 4 + 3]).normal()
        if negate:
            vector *= -1
        return [vector.x, vector.y, vector.z]

    def aim_at(
        self,
        target: "mref.ReferencedItem|str|list[float]",
        aim_vector: list[float] = (1.0, 0.0, 0.0),
        up_vector: list[float] = (0.0, 1.0, 0.0),
        world_up_vector: list[float] = (0.0, 1.0, 0.0),
        world_up_object: "mref.ReferencedItem|str|None" = None,
    ) -> None:
        """
        Rotates this node so its ``aim_vector`` axis points at the
        target. This is a one-off snap (a temporary aim constraint is
        created and removed), not a live constraint.

        :param target: A node, or a world-space position ``[x, y, z]``.
        :param aim_vector: The local axis to point at the target.
        :param up_vector: The local axis to align with the world up.
        :param world_up_vector: The world-space up direction, used when
            no ``world_up_object`` is given.
        :param world_up_object: If given, the up axis aims at this
            node's position instead of following ``world_up_vector``.
        """
        temporary = []

        try:
            if isinstance(target, (list, tuple)):
                target_name = cmds.createNode("transform", name="mref_aim_target")
                temporary.append(target_name)
                cmds.xform(target_name, translation=list(target), worldSpace=True)
            else:
                target_name = mref.get(target).full_name()

            kwargs = dict(
                aimVector=list(aim_vector),
                upVector=list(up_vector),
                worldUpVector=list(world_up_vector),
                worldUpType="vector",
            )
            if world_up_object is not None:
                kwargs["worldUpType"] = "object"
                kwargs["worldUpObject"] = mref.get(world_up_object).full_name()

            temporary.extend(
                cmds.aimConstraint(
                    target_name,
                    self.item.full_name(),
                    maintainOffset=False,
                    **kwargs
                )
            )
        finally:
            if temporary:
                cmds.delete(temporary)

    @staticmethod
    def _limit_flag(channel: str) -> str:
        """
        Returns the ``cmds.transformLimits`` flag (``tx``, ``ry`` ...)
        for the given channel name. Raises ``ValueError`` for anything
        that is not a translate, rotate or scale channel.
        """
        flag = _LIMIT_CHANNELS.get(channel, channel)
        if flag not in _LIMIT_CHANNELS.values():
            raise ValueError(
                f"Unsupported limit channel {channel!r}; expected a translate, "
                "rotate or scale channel such as 'tx' or 'rotateY'"
            )
        return flag

    @staticmethod
    def _space_kwargs(space: str) -> dict:
        """
        Returns the ``cmds.xform`` kwargs dict for the given space name.
        Raises ``ValueError`` for unknown spaces.
        """
        if space == "object":
            return {"objectSpace": True}
        if space == "world":
            return {"worldSpace": True}
        raise ValueError(
            f"Unsupported space {space!r}; expected one of {_SUPPORTED_SPACES}"
        )