import aniseed
import maya.cmds as mc


# --------------------------------------------------------------------------------------
class MayaConfigStandard(aniseed.RigConfiguration):

    identifier = "Rig Configuration : Standard"
    version = 3

    # ----------------------------------------------------------------------------------
    def create_component_structure(self):

        global_joint = mc.rename(
            mc.joint(),
            self.generate_name(
                classification=self.joint,
                description="global_srt",
                location=self.middle,
            ),
        )

        # -- Lets pre-load our Standard rigs with a series of components
        sub_struct = self.rig.add_component(
            component_type="Utility : Add Sub Structure",
            label="Define Rig Structure",
            requirements={
                "Parent": self.rig.label,
            },
            options={
                "Sub Nodes": [
                    "skeleton",
                    "controls",
                    "geometry",
                ]
            },
        )

        self.rig.add_component(
            component_type="Basics : Reparent",
            label="Parent Skeleton",
            requirements={
                "Node To Re-Parent": global_joint,
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

        store_shapes = self.rig.add_component(
            component_type="Utility : Store Control Shapes",
            label="Store Shapes",
            parent=make_editable,
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
            parent=store_shapes,
        )

        build_rig = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Build Control Rig",
        )

        self.rig.add_component(
            component_type="Core : Global Control Root",
            label="Global SRT",
            requirements={
                "Joint To Drive": global_joint,
                "Parent": self.generate_name(
                    classification=self.organisational,
                    description="controls",
                    location=self.middle,
                )
            },
            parent=build_rig,
        )

        apply_shapes = self.rig.add_component(
            component_type="Utility : Apply Control Shapes",
            label="Apply Shapes",
            parent=build_rig,
        )

        self.rig.add_component(
            component_type="Utility : Color Controls",
            label="Color Controls",
            parent=apply_shapes,
        )

        return