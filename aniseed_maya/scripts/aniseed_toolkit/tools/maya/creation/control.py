import aniseed
import aniseed_toolkit

class CreateControl(aniseed_toolkit.Tool):

    identifier = "Create Control"
    classification = "Rigging"
    user_facing = False

    # --------------------------------------------------------------------------------------
    # noinspection PyUnresolvedReferences
    def run(
            self,
            description: str = "",
            location: str = "",
            parent: str = "",
            shape: str = "",
            config: "aniseed.RigConfiguration" = None,
            match_to: str = None,
            shape_scale: float = 1.0,
            rotate_shape=None,
            classification_override=None
    ) -> "Control":
        """
        This will create a control structure. It is not mandatory to use this within the
        rigging framework, but by doing so you will have a consistent behaviour with all
        components that come packaged with the rigging tool.

        Args:
            description (str): Descriptive part of the nodes name
            location (str): Location of the control
            parent (str): Parent of the control
            shape (str): Shape of the control to apply (should be accessible via
                aniseed_toolkit/_resources/shapes
            config: The rig configuration instance
            match_to: Optional object to match transform to
            shape_scale: Scale of the shape to apply to the control, default is 1.0
            rotate_shape: Optional object to rotate shape to apply to the control, default is None
            classification_override: By default this will always use the control
                prefix as per the rig configuration, but you can specify an override.

        Returns:
            Control: The created control which has an accessor for the zero,
                offset, and org node which makes up a controls hierarchy.
        """
        return aniseed_toolkit.rig.control.create(
            description=description,
            location=location,
            parent=parent,
            shape=shape,
            config=config,
            match_to=match_to,
            shape_scale=shape_scale,
            rotate_shape=rotate_shape,
            classification_override=classification_override
        )
