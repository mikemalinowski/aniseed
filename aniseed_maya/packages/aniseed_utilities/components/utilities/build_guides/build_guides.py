"""
Provides the "Utility : Build All Guides" and "Utility : Remove All Guides"
components. These call user_func_create_guide or user_func_remove_guide on
every component in the stack which defines it, giving a single entry point
for building or tearing down all guide rigs.
"""
import aniseed


class BuildGuidesComponent(aniseed.RigComponent):
    """
    Iterates every component on the stack and invokes its
    ``user_func_create_guide`` callback, if one is defined. Provides a
    single entry point for building the guide rigs of every component
    that opts in to the guide protocol.
    """

    identifier = "Utility : Build All Guides"

    def run(self):
        """
        Calls user_func_create_guide on every component in the stack which
        defines it.
        """
        for component in self.stack.components():
            if hasattr(component, 'user_func_create_guide'):
                component.user_func_create_guide()


class RemoveGuidesComponent(aniseed.RigComponent):
    """
    Iterates every component on the stack and invokes its
    ``user_func_remove_guide`` callback, if one is defined. The inverse
    of :class:`BuildGuidesComponent` — tears down any guide rigs that
    were created by the matching build pass.
    """

    identifier = "Utility : Remove All Guides"

    def run(self):
        """
        Calls user_func_remove_guide on every component in the stack which
        defines it.
        """
        for component in self.stack.components():
            if hasattr(component, 'user_func_remove_guide'):
                component.user_func_remove_guide()
