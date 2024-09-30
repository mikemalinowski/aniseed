import aniseed_everywhere

from crosswalk import app


# --------------------------------------------------------------------------------------
class RigConfigurationBasic(aniseed_everywhere.RigConfiguration):
    """
    The RigConfiguration is a special Rig Component. Every Rig instance must have a rig
    configuration item in its stack in order to build.

    This configuration will expose all its parameters to the user to tailor. Alternatively
    you can implement your own components providing you exose all the same properties and
    methods.

    If you implement your own config compnent it should always start wtih "Rig Configuration :"
    """
    identifier = "Rig Configuration : Standard"

    version = 2.0

    # --------------------------------------------------------------------------------------
    def create_component_structure(self):
        global_joint = app.objects.create(
            self.generate_name(
                classification=self.joint,
                description="GlobalSrt",
                location=self.middle,
            ),
        )

        # -- Lets pre-load our Standard rigs with a series of components
        sub_struct = self.rig.add_component(
            component_type="Utility : Add Sub Structure",
            label="Define Rig Structure",
            requirements={
                "Parent": app.objects.get_name(self.rig.host()),
            },
            options={
                "Sub Nodes": [
                    "skeleton",
                    "controls",
                    "geometry",
                    "guides",
                ]
            },
        )

        self.rig.add_component(
            component_type="Utility : Reparent",
            label="Parent Skeleton",
            requirements={
                "Node To Re-Parent": app.objects.get_name(global_joint),
                "New Parent": self.generate_name(
                    classification=self.organisational,
                    description="skeleton",
                    location=self.middle,
                )
            },
            parent=sub_struct,
        )

        make_editable = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Make Rig Editable",
        )

        self.rig.add_component(
            component_type="Utility : Delete Children",
            label="Clear Control Rig",
            requirements={
                "Node": self.generate_name(
                    classification=self.organisational,
                    description="controls",
                    location=self.middle,
                ),
            },
            parent=make_editable,
        )

        build_rig = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Build Control Rig",
        )

