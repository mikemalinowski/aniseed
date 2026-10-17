import mref
from maya import cmds
from maya.api import OpenMaya as om


class Follicle(mref.Trait):
    """
    Trait bound to any node with ``MFn.kFollicle`` — follicle shape
    nodes, used both for hair systems and as surface-pinned rivets.
    Exposes the UV parameters, the mesh or NURBS surface the follicle
    is attached to, attaching / detaching it, driving the follicle's
    transform from its outputs, the evaluated world position, rotation
    and normal, and the hair system it feeds.
    """

    # -- Sits above the generic Shape trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kFollicle)

    def parameter_u(self) -> float:
        """
        Returns the U parameter (0-1) at which the follicle sits
        """
        return cmds.getAttr(f"{self.item.full_name()}.parameterU")

    def set_parameter_u(self, value: float) -> None:
        """
        Sets the U parameter (0-1) at which the follicle sits
        """
        cmds.setAttr(f"{self.item.full_name()}.parameterU", value)

    def parameter_v(self) -> float:
        """
        Returns the V parameter (0-1) at which the follicle sits
        """
        return cmds.getAttr(f"{self.item.full_name()}.parameterV")

    def set_parameter_v(self, value: float) -> None:
        """
        Sets the V parameter (0-1) at which the follicle sits
        """
        cmds.setAttr(f"{self.item.full_name()}.parameterV", value)

    def surface(self) -> mref.ReferencedItem|None:
        """
        Returns the mesh or NURBS surface shape the follicle is attached
        to (the source of ``inputMesh`` or ``inputSurface``), or None if
        it is not attached.
        """
        for attribute in ("inputMesh", "inputSurface"):
            sources = cmds.listConnections(
                f"{self.item.full_name()}.{attribute}",
                source=True,
                destination=False,
                shapes=True,
            ) or []
            if sources:
                return mref.get(sources[0])
        return None

    def attach_to(
        self,
        shape: "mref.ReferencedItem|str",
        u: float|None = None,
        v: float|None = None,
        drive_transform: bool = True,
    ) -> None:
        """
        Attaches the follicle to a mesh or NURBS surface. A transform
        may be given, in which case its first shape is used. Connects
        ``worldMatrix[0]`` to ``inputWorldMatrix`` and either
        ``outMesh`` to ``inputMesh`` or ``local`` to ``inputSurface``.

        Optionally sets the U / V parameters, and when
        ``drive_transform`` is True (default) wires the follicle's
        outputs onto its transform (see :meth:`drive_transform`).
        """
        shape = mref.get(shape)
        shape_pointer = shape.pointer()

        if not shape_pointer.hasFn(om.MFn.kShape):
            shape = shape.shape()
            if shape is None:
                raise RuntimeError("Given node has no shape to attach to")
            shape_pointer = shape.pointer()

        shape_name = shape.full_name()
        follicle_name = self.item.full_name()

        if shape_pointer.hasFn(om.MFn.kMesh):
            cmds.connectAttr(f"{shape_name}.outMesh", f"{follicle_name}.inputMesh", force=True)
        elif shape_pointer.hasFn(om.MFn.kNurbsSurface):
            cmds.connectAttr(f"{shape_name}.local", f"{follicle_name}.inputSurface", force=True)
        else:
            raise RuntimeError(f"{shape_name} is not a mesh or NURBS surface")

        cmds.connectAttr(
            f"{shape_name}.worldMatrix[0]",
            f"{follicle_name}.inputWorldMatrix",
            force=True,
        )

        if u is not None:
            self.set_parameter_u(u)
        if v is not None:
            self.set_parameter_v(v)

        if drive_transform:
            self.drive_transform()

    def detach(self) -> None:
        """
        Disconnects the follicle from the surface it is attached to
        (``inputMesh``, ``inputSurface`` and ``inputWorldMatrix``).
        """
        for attribute in ("inputMesh", "inputSurface", "inputWorldMatrix"):
            destination = f"{self.item.full_name()}.{attribute}"
            sources = cmds.listConnections(
                destination,
                source=True,
                destination=False,
                plugs=True,
            ) or []
            for source in sources:
                cmds.disconnectAttr(source, destination)

    def drive_transform(self) -> None:
        """
        Connects ``outTranslate`` / ``outRotate`` to the translate and
        rotate of the follicle's transform, so the transform rides the
        surface. This is the standard rivet / hair follicle setup.
        """
        transform = self.item.parent()
        if transform is None:
            return

        for output, channel in (("outTranslate", "translate"), ("outRotate", "rotate")):
            destination = f"{transform.full_name()}.{channel}"
            if not cmds.isConnected(f"{self.item.full_name()}.{output}", destination):
                cmds.connectAttr(f"{self.item.full_name()}.{output}", destination, force=True)

    def world_position(self) -> list[float]:
        """
        Returns the evaluated world-space position ``[x, y, z]`` of the
        follicle on its surface (``outTranslate``).
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.outTranslate")[0])

    def world_rotation(self) -> list[float]:
        """
        Returns the evaluated world-space rotation ``[x, y, z]`` in
        degrees of the follicle on its surface (``outRotate``).
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.outRotate")[0])

    def surface_normal(self) -> list[float]:
        """
        Returns the evaluated surface normal ``[x, y, z]`` at the
        follicle's position (``outNormal``).
        """
        return list(cmds.getAttr(f"{self.item.full_name()}.outNormal")[0])

    def hair_system(self) -> mref.ReferencedItem|None:
        """
        Returns the hair system shape this follicle feeds (via
        ``outHair``), or None if it is not part of a hair system.
        """
        destinations = cmds.listConnections(
            f"{self.item.full_name()}.outHair",
            source=False,
            destination=True,
            shapes=True,
            type="hairSystem",
        ) or []
        if destinations:
            return mref.get(destinations[0])
        return None
