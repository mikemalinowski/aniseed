"""
Provides the "Dev Example : Add Child Components" component, a "template"
component which adds a joint chain and a control beneath itself, already
wired together.

What this example teaches:
    * Adding components from code with rig.add_component
    * Wiring components together by writing addresses
    * Passing a parent's inputs down to its children
    * Why the stack must not be changed during a build

Read next: ../07_config/ex15_example_config.py
"""
import typing
import logging

import aniseed

log = logging.getLogger(__name__)


class AddChildComponents(aniseed.RigComponent):
    """
    Adds a Joint Chain (cmds) and a Simple Control beneath this component,
    with the control driving the root of the chain. Set the guides and
    parents here: the children read them from this component.
    """

    identifier = "Dev Example : Add Child Components"

    # -- The identifiers of the components this template adds
    CHAIN_TYPE = "Dev Example : Joint Chain (cmds)"
    CONTROL_TYPE = "Dev Example : Simple Control"

    def __init__(self, *args, **kwargs):
        """
        Declares the guide and parent inputs which are passed down to the
        children, and the Description and Add Children On Enter Stack options.
        """
        super().__init__(*args, **kwargs)

        # -- These inputs are not used by this component's own run, only by
        # -- its children, so they are not required here. The children check
        # -- them when they validate.
        self.declare_input(
            name="Start Guide",
            value="",
            validate=False,
            description="Passed to the chain's Start input",
            group="Guides",
        )
        self.declare_input(
            name="End Guide",
            value="",
            validate=False,
            description="Passed to the chain's End input",
            group="Guides",
        )
        self.declare_input(
            name="Skeleton Parent",
            value="",
            validate=False,
            description="Passed to the chain's Parent input",
            group="Parents",
        )
        self.declare_input(
            name="Control Parent",
            value="",
            validate=False,
            description="Passed to the control's Parent input",
            group="Parents",
        )

        self.declare_option(
            name="Description",
            value="template",
            description="The description given to the chain and the control",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Add Children On Enter Stack",
            value=True,
            description="If on, the children are added as soon as this component is added",
            group="Behaviour",
            pre_expose=True,
        )

    def input_widget(self, requirement_name):
        """
        Returns an object selector for every input.
        """
        return aniseed.widgets.ObjectSelector(component=self)

    def user_functions(self) -> typing.Dict[str, callable]:
        """
        Adds an "Add Child Components" menu entry, so the children can be
        added again if they are deleted.
        """
        return {
            "Add Child Components": self.add_child_components,
        }

    def on_enter_stack(self):
        """
        Adds the children when the user adds this component, if Add Children
        On Enter Stack is on. Not called when a recipe loads, so a loaded
        template keeps exactly the children it was saved with.
        """
        super().on_enter_stack()

        if self.option("Add Children On Enter Stack").get():
            self.add_child_components()

    def run(self):
        """
        Does nothing. A component's children are built straight after it, in
        order, so the chain and the control build next.
        """
        return True

    def add_child_components(self):
        """
        Adds whichever of the chain and the control are not already children
        of this component, and wires them up.
        """
        # -- Key idea: never add or remove components while the rig is
        # -- building. The build has already worked out which components to
        # -- run, so the change would be missed, or worse, half applied. That
        # -- is why this is done from on_enter_stack and the menu, and never
        # -- from run.
        if self.rig.is_building():
            log.warning(f"{self.label()} : cannot add components while the rig is building")
            return

        # -- Addresses are split on full stops, so a label containing one
        # -- would produce addresses which cannot be resolved
        if "." in self.label():
            log.error(f"{self.label()} : labels used in addresses cannot contain a full stop")
            return

        # -- Guard against adding the children twice, such as when the menu
        # -- entry is used on a template which already has them
        existing_types = [child.identifier for child in self.children]

        description = self.option("Description").get()
        chain_label = f"{self.label()} Chain"
        control_label = f"{self.label()} Control"

        if self.CHAIN_TYPE not in existing_types:
            self.rig.add_component(
                component_type=self.CHAIN_TYPE,
                label=chain_label,
                # -- input.address() gives the address of one of OUR inputs,
                # -- such as "[Template].[input].[Start Guide]". The child
                # -- reads whatever this template's input holds at build
                # -- time, so the guides only ever need setting in one place.
                inputs={
                    "Start": self.input("Start Guide").address(),
                    "End": self.input("End Guide").address(),
                    "Parent": self.input("Skeleton Parent").address(),
                },
                options={
                    "Description": f"{description}_chain",
                },
                # -- parent places the new component beneath this one in
                # -- the stack, so it builds straight after this one
                parent=self,
            )

        if self.CONTROL_TYPE not in existing_types:
            self.rig.add_component(
                component_type=self.CONTROL_TYPE,
                label=control_label,
                inputs={
                    "Parent": self.input("Control Parent").address(),
                    # -- An address can also be written by hand. This one
                    # -- points at the chain's Root Joint output.
                    "Joint to Drive": f"[{chain_label}].[output].[Root Joint]",
                },
                options={
                    "Description": description,
                },
                parent=self,
            )
