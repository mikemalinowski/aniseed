import aniseed


class BuildGuidesComponent(aniseed.RigComponent):

    identifier = "Utility : Build All Guides"

    def run(self):
        for component in self.stack.components():
            if hasattr(component, 'user_func_create_guide'):
                component.user_func_create_guide()


class RemoveGuidesComponent(aniseed.RigComponent):

    identifier = "Utility : Remove All Guides"

    def run(self):
        for component in self.stack.components():
            if hasattr(component, 'user_func_remove_guide'):
                component.user_func_remove_guide()
