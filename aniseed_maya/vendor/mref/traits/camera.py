import mref
from maya import cmds
from maya.api import OpenMaya as om


class Camera(mref.Trait):
    """
    Trait bound to any node with ``MFn.kCamera`` — camera shape nodes.
    Exposes the lens (focal length, film aperture, field of view), the
    clipping planes, orthographic state and the world-space view vectors
    (eye point, view direction, up direction), plus an aim helper.

    Film aperture values are in inches (Maya's native unit for
    ``horizontalFilmAperture``/``verticalFilmAperture``), focal length in
    millimetres, field of view in degrees and distances in scene units.
    """

    # -- Sits above the generic Shape trait
    priority = 1

    @classmethod
    def can_bind(cls, pointer: om.MObject) -> bool:
        """
        This determines whether this trait can be bound to the given object
        """
        return isinstance(pointer, om.MObject) and pointer.hasFn(om.MFn.kCamera)

    def focal_length(self) -> float:
        """
        Returns the focal length of the camera in millimetres
        """
        return self._camera().focalLength

    def set_focal_length(self, value: float) -> None:
        """
        Sets the focal length of the camera in millimetres
        """
        cmds.setAttr(f"{self.item.full_name()}.focalLength", value)

    def film_aperture(self) -> list[float]:
        """
        Returns the ``[horizontal, vertical]`` film aperture in inches
        """
        camera = self._camera()
        return [camera.horizontalFilmAperture, camera.verticalFilmAperture]

    def set_film_aperture(self, horizontal: float, vertical: float) -> None:
        """
        Sets the horizontal and vertical film aperture in inches
        """
        cmds.setAttr(f"{self.item.full_name()}.horizontalFilmAperture", horizontal)
        cmds.setAttr(f"{self.item.full_name()}.verticalFilmAperture", vertical)

    def clip_planes(self) -> list[float]:
        """
        Returns the ``[near, far]`` clipping plane distances
        """
        camera = self._camera()
        return [camera.nearClippingPlane, camera.farClippingPlane]

    def set_clip_planes(self, near: float|None = None, far: float|None = None) -> None:
        """
        Sets the near and/or far clipping plane distances. Either value
        may be None to leave it unchanged.
        """
        if near is not None:
            cmds.setAttr(f"{self.item.full_name()}.nearClipPlane", near)
        if far is not None:
            cmds.setAttr(f"{self.item.full_name()}.farClipPlane", far)

    def is_orthographic(self) -> bool:
        """
        Returns True if this camera uses an orthographic projection
        """
        return self._camera().isOrtho()

    def set_orthographic(self, state: bool, width: float|None = None) -> None:
        """
        Switches the camera in or out of orthographic projection. If
        ``width`` is given it is applied as the orthographic width.
        """
        cmds.setAttr(f"{self.item.full_name()}.orthographic", state)
        if width is not None:
            self.set_ortho_width(width)

    def ortho_width(self) -> float:
        """
        Returns the width of the view when the camera is orthographic
        """
        return cmds.getAttr(f"{self.item.full_name()}.orthographicWidth")

    def set_ortho_width(self, width: float) -> None:
        """
        Sets the width of the view used when the camera is orthographic
        """
        cmds.setAttr(f"{self.item.full_name()}.orthographicWidth", width)

    def field_of_view(self) -> list[float]:
        """
        Returns the ``[horizontal, vertical]`` field of view in degrees,
        derived from the focal length and film aperture.
        """
        camera = self._camera()
        return [
            om.MAngle(camera.horizontalFieldOfView()).asDegrees(),
            om.MAngle(camera.verticalFieldOfView()).asDegrees(),
        ]

    def eye_point(self) -> list[float]:
        """
        Returns the world-space position of the camera's eye point
        """
        point = self._camera().eyePoint(om.MSpace.kWorld)
        return [point.x, point.y, point.z]

    def view_direction(self) -> list[float]:
        """
        Returns the normalised world-space direction the camera looks along
        """
        vector = self._camera().viewDirection(om.MSpace.kWorld).normal()
        return [vector.x, vector.y, vector.z]

    def up_direction(self) -> list[float]:
        """
        Returns the normalised world-space up vector of the camera
        """
        vector = self._camera().upDirection(om.MSpace.kWorld).normal()
        return [vector.x, vector.y, vector.z]

    def look_at(self, target: "list[float]|mref.ReferencedItem|str") -> None:
        """
        Rotates the camera's transform so that it looks at the given
        target, which may be a world-space ``[x, y, z]`` point or a
        node (whose world-space pivot is used). The camera's centre of
        interest is updated to the target distance.
        """
        if isinstance(target, mref.ReferencedItem):
            target = target.full_name()

        if isinstance(target, str):
            target = cmds.xform(target, query=True, worldSpace=True, rotatePivot=True)

        cmds.viewPlace(self.item.full_name(), lookAt=list(target))

    def _camera(self) -> om.MFnCamera:
        # -- Built from a fresh DAG path each time so world-space queries
        # -- stay correct after the camera is re-parented.
        return om.MFnCamera(om.MDagPath.getAPathTo(self._pointer))
