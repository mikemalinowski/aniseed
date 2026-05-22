import typing

import mref
from maya.api import OpenMaya as om
from maya import cmds


_SUPPORTED_SPACES = ("object", "world")


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