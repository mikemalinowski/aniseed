import aniseed
from maya import cmds


class MayaConfigStandard(aniseed.RigConfiguration):

    identifier = "Rig Configuration : Standard"
    version = 3

    def __init__(self, *args, **kwargs):
        super(MayaConfigStandard, self).__init__(*args, **kwargs)

    def on_enter_stack(self):
        self.create_component_structure()

    def create_component_structure(self):

        control_org_name = self.generate_name(
            classification=self.organisational,
            description="controls",
            location=self.middle,
        )

        skeleton_org_name = self.generate_name(
            classification=self.organisational,
            description="skeleton",
            location=self.middle,
        )

        # -- Lets pre-load our Standard rigs with a series of components
        sub_struct = self.rig.add_component(
            component_type="Utility : Add Sub Structure",
            label="Define Rig Structure",
            inputs={
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

        reparent_component = self.rig.add_component(
            component_type="Utility : Reparent",
            label="Parent Skeleton",
            inputs={
                "Node To Re-Parent": "",
                "New Parent": skeleton_org_name
            },
            parent=sub_struct,
        )

        # -- Create the edit structure
        edit_component = self.create_editable_structure(None, skeleton_org_name, control_org_name)
        build_component = self.create_rig_structure(None, skeleton_org_name, control_org_name)

        srt_component = self.rig.get_component_by_label("Global SRT")
        created_joint = srt_component.input("Joint To Drive").get()
        reparent_component.input("Node To Re-Parent").set(created_joint)

        self.stack.build()
        self.stack.build(build_below=edit_component)

        # -- Finally we will remove the two placeholder components
        self.stack.remove_component(sub_struct)

        # -- Finally select the root joint for the user
        cmds.select(created_joint)
        return

    def create_editable_structure(self, parent, skeleton_org_name, control_org_name):

        make_editable = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Make Rig Editable",
        )

        show_skeleton = self.rig.add_component(
            component_type="Utility : Show/Hide",
            label="Show Skeleton",
            inputs={
                "Nodes To Set Visibility": [skeleton_org_name]
            },
            parent=make_editable,
        )

        store_shapes = self.rig.add_component(
            component_type="Utility : Store Control Shapes",
            label="Store Shapes",
            parent=make_editable,
        )

        self.rig.add_component(
            component_type="Utility : Delete Children",
            label="Clear Control Rig",
            inputs={
                "Node": control_org_name,
            },
            parent=store_shapes,
        )

        self.rig.add_component(
            component_type="Utility : Build All Guides",
            label="Build All Guides",
            parent=make_editable,
        )

        return make_editable

    def create_rig_structure(self, parent, skeleton_org_name, control_org_name):

        build_rig = self.rig.add_component(
            component_type="Stack : Organiser",
            label="Build Control Rig",
        )

        self.rig.add_component(
            component_type="Utility : Remove All Guides",
            label="Remove All Guides",
            parent=build_rig,
        )

        root_component = self.rig.add_component(
            component_type="Core : Global Control Root",
            label="Global SRT",
            inputs={
                "Parent": control_org_name
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

        self.rig.add_component(
            component_type="Utility : Type Driven Show/Hide",
            label="Hide Mechanicals",
            inputs={
                "Nodes To Search Under": [control_org_name],
            },
            options={
                "Node Types to Hide": [
                    "joint",
                    "ikHandle",
                ],
            },
            parent=build_rig,
        )

        self.rig.add_component(
            component_type="Utility : Show/Hide",
            label="Hide Skeleton",
            parent=build_rig,
            inputs={
                "Nodes To Set Visibility": [skeleton_org_name],
            },
            options={
                "Visibility": False,
            },
        )

        return build_rig
