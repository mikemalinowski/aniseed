"""
Provides the "Augment : Insert Control" component, which creates a control
beneath a parent node and optionally moves the parent's existing transform
children under that control.
"""
import logging
import mref
import aniseed
import aniseed_toolkit
from aniseed_maya_standard.mixins import MirrorMixin

log = logging.getLogger(__name__)


class InsertControlComponent(aniseed.RigComponent, MirrorMixin):
    """
    Inserts a new control between a parent node and its existing
    children. The control is created as a child of ``Parent`` and,
    if "Move All Children Under Control" is enabled, every transform
    child of ``Parent`` is re-parented under the new control so the
    control sits in the middle of the hierarchy.
    """

    identifier = "Augment : Insert Control"

    def __init__(self, *args, **kwargs):
        """
        Declares the "Parent" input, the "Move All Children Under Control",
        match, naming and shape options, and the "Control" output.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            description=(
                "The node above the point where the new control will "
                "be inserted. The control becomes a child of this node."
            ),
            value="",
            validate=True,
            group="Required Joint",
        )

        self.declare_option(
            name="Move All Children Under Control",
            description=(
                "If enabled, every transform child of ``Parent`` is "
                "re-parented under the new control after creation."
            ),
            value=True,
            group="Behaviour",
        )

        self.declare_option(
            name="Match Transform To",
            description=(
                "Optional node whose world transform the new control "
                "will be matched to. Leave empty to match the parent."
            ),
            value="",
            group="Behaviour",
        )

        self.declare_option(
            name="Name",
            description="Descriptive name token used when generating the control's name.",
            value="",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            description=(
                "Location token (c/l/r/f/b) used when generating the "
                "control's name. Inherited from the parent component "
                "when added to the stack."
            ),
            value=self.config.middle,
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_option(
            name="Shape",
            description="Aniseed-toolkit control shape used for the inserted control.",
            value="core_cube",
            group="Visuals",
        )

        self.declare_output(
            "Control",
            description="The newly-created control node.",
        )

    def option_widget(self, option_name: str):
        """
        Returns a location selector for "Location", a shape selector for
        "Shape" and an object selector for "Match Transform To", or None
        otherwise.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(config=self.config)

        if option_name == "Shape":
            return aniseed.widgets.ShapeSelector(
                default_item=self.option("Shape").get(),
            )

        if option_name == "Match Transform To":
            return aniseed.widgets.ObjectSelector(component=self)

    def suggested_label(self):
        """
        Builds a label from the "Name" and upper-cased "Location" options.
        """
        name = self.option("Name").get()
        location = self.option("Location").get().upper()

        return f"Insert {name} Control {location}"

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for the "Parent" input, or None otherwise.

        Args:
            requirement_name: The name of the input to return a widget for.
        """
        if requirement_name == "Parent":
            return aniseed.widgets.ObjectSelector(component=self)

        return None

    def is_valid(self) -> bool:
        """
        Checks that the "Parent" input and the "Name" option are given.
        """
        if not self.input("Parent").get():
            log.warning(f"{self.label()} : Parent is not set")
            return False

        if not self.option("Name").get():
            log.warning(f"{self.label()} : Name is empty, so the control cannot be named")
            return False

        return True

    def run(self) -> bool:
        """
        Creates a control beneath the parent (matched to the parent unless a
        match node is given) and, if enabled, moves the parent's transform
        children under it. The children are gathered before the control is
        created so the control itself is not re-parented.
        """

        parent = mref.get(self.input("Parent").get())

        # -- Gather the children before the control is added beneath the parent
        children = parent.children(node_type="transform")

        control = aniseed_toolkit.rig.control.create(
            description=self.option("Name").get(),
            location=self.option("Location").get(),
            parent=parent.full_name(),
            config=self.config,
            shape=self.option("Shape").get(),
            match_to=self.option("Match Transform To").get() or parent.full_name(),
        )
        self.output("Control").set(control.ctl)

        control = mref.get(control.ctl)

        if self.option("Move All Children Under Control").get():
            control.add_children(children)

        return True
