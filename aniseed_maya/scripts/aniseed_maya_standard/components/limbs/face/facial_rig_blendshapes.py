"""
Provides the "TPS : BlendShape Based Facial Rig" component, which replaces
any blendshapes on a base mesh with one built from the given target shapes and
builds high level facial controls to drive its weights. Also provides the
"TPS : Link BlendShapes" component, which connects the aliased weights of a
driving blendshape to the matching weights of other blendshapes.
"""
import mref
import aniseed
import aniseed_toolkit


# noinspection PyUnresolvedReferences
class BlendshapeFacialRig(aniseed.RigComponent):
    """
    Builds a set of high level facial controls which drive the weights of a
    blendshape created from the given target shapes.
    """

    identifier = "TPS : BlendShape Based Facial Rig"

    shape_list = [

        "left_lip_corner_push_in",
        "left_lip_corner_pull_out",
        "left_lip_corner_pull_up",
        "left_lip_corner_pull_down",
        "left_lip_sneer_lower",
        "left_lip_sneer_upper",
        "left_cheek_suck",
        "left_cheek_blow",
        "left_nose_flare",
        "left_squint_inner",
        "left_squint_outer",

        "right_lip_corner_push_in",
        "right_lip_corner_pull_out",
        "right_lip_corner_pull_up",
        "right_lip_corner_pull_down",
        "right_lip_sneer_lower",
        "right_lip_sneer_upper",
        "right_cheek_suck",
        "right_cheek_blow",
        "right_nose_flare",
        "right_squint_inner",
        "right_squint_outer",

        "upper_sneer",
        "lower_sneer",

        "upper_lip_pull",
        "lower_lip_pull",
        "upper_lip_compress",
        "lower_lip_compress",
        "upper_lip_curl_out",
        "lower_lip_curl_out",
        "upper_lip_curl_in",
        "lower_lip_curl_in",

        "left_brow_inner_up",
        "left_brow_inner_down",
        "left_brow_inner_in",
        "left_brow_outer_up",
        "left_brow_outer_down",
        "left_brow_mid_up",
        "left_brow_mid_down",

        "right_brow_inner_up",
        "right_brow_inner_down",
        "right_brow_inner_in",
        "right_brow_outer_up",
        "right_brow_outer_down",
        "right_brow_mid_up",
        "right_brow_mid_down",
    ]

    control_groups = [
        "left_lip_corner",
        "right_lip_corner",
        "upper_lip",
        "lower_lip",
        "nose",
        "left_brow_inner",
        "left_brow_outer",
        "right_brow_inner",
        "right_brow_outer",
    ]

    def __init__(self, *args, **kwargs):
        """
        Declares the parent and base mesh inputs, one (optional) target shape
        input per entry in shape_list grouped by side, and control, parent,
        guide and shape options for each control group.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            group="Control Rig",
        )

        self.declare_input(
            name="Base Mesh",
            value="",
            group="Control Rig",
        )

        for shape_label in self.shape_list:
            side = "Central"
            if shape_label.startswith("left"):
                side = "Left"
            if shape_label.startswith("right"):
                side = "Right"

            self.declare_input(
                name=shape_label,
                value="",
                group=f"{side} Shapes",
                validate=False,
            )

        # -- Each control group can be given a pre-made control, a parent,
        # -- a guide and a shape
        control_group_parts = [
            ("control", ""),
            ("parent", ""),
            ("guide", ""),
            ("shape", "core_cube"),
        ]
        for control_label in self.control_groups:
            group = "Control : %s" % control_label.replace("_", " ").title()

            for part, value in control_group_parts:
                self.declare_option(
                    name=f"{control_label}_{part}",
                    value=value,
                    group=group,
                )

    def input_widget(self, requirement_name: str):
        """
        Returns an object selector for every input.
        """
        return aniseed.widgets.ObjectSelector()

    def option_widget(self, requirement_name: str):
        """
        Returns a shape selector for the control group "_shape" options and an
        object selector for all other options.
        """
        if requirement_name.endswith("_shape"):
            return aniseed.widgets.ShapeSelector(default_item="core_cube")

        return aniseed.widgets.ObjectSelector()

    def run(self):
        """
        Removes any existing blendshapes from the base mesh, creates a new one
        from the given target shapes and builds the lip corner, central lip,
        nose and brow controls to drive its weights.
        """
        base_mesh = mref.get(self.input("Base Mesh").get())
        parent = self.input("Parent").get()

        self.remove_blendshapes(base_mesh)

        # -- The control settings for this component are stored as options
        # -- and no proxies are exposed
        control_rig = aniseed_toolkit.rigging.facial.FacialControlRig(
            config=self.config,
            read_setting=lambda name: self.option(name).get(),
        )

        attribute_dictionary = self.setup_blendshape(base_mesh)
        addition_nodes = control_rig.initialise_driving_adds(attribute_dictionary)

        # -- Note: the order of these calls decides the array indices on the
        # -- plusMinusAverage nodes, so it must be preserved.
        for location in ["left", "right"]:
            control_rig.setup_lip_puller(
                location=location,
                guide=self.option(f"{location}_lip_corner_guide").get(),
                parent=parent,
                connection_map=addition_nodes,
            )

        for section in ["upper", "lower"]:
            control_rig.setup_central_lip(
                section=section,
                guide=self.option(f"{section}_lip_guide").get(),
                parent=parent,
                connection_map=addition_nodes,
            )

        control_rig.setup_nose(
            guide=self.option("nose_guide").get(),
            parent=parent,
            connection_map=addition_nodes,
        )

        for location in ["left", "right"]:
            control_rig.setup_inner_brow(
                location=location,
                guide=self.option(f"{location}_brow_inner_guide").get(),
                parent=parent,
                connection_map=addition_nodes,
            )

        for location in ["left", "right"]:
            control_rig.setup_outer_brow(
                location=location,
                guide=self.option(f"{location}_brow_outer_guide").get(),
                parent=parent,
                connection_map=addition_nodes,
            )

    def setup_blendshape(self, base_mesh: mref.ReferencedItem) -> dict:
        """
        Creates the blendshape on the base mesh from all the specified target
        shapes and returns a dictionary of shape label to weight attribute.
        """
        targets = []
        input_names = []

        for input_name in self.shape_list:
            target = self.input(input_name).get()

            if not target:
                continue

            targets.append(target)
            input_names.append(input_name)

        blendshape_node = mref.blendShape(
            targets + [base_mesh.name()],
            automatic=True,
            name=self.config.generate_name(
                classification="blendshape",
                description="face",
                location=self.config.middle,
            )
        )[0]

        return {
            input_name: blendshape_node.attr(f"weight[{idx}]")
            for idx, input_name in enumerate(input_names)
        }

    @staticmethod
    def remove_blendshapes(mesh: mref.ReferencedItem):
        """
        Remove all blendShape nodes from a mesh while preserving skinning.

        Args:
            mesh: transform or shape

        Returns:
            list: removed blendShape nodes
        """
        # -- Get shape if transform passed
        shapes = mref.listRelatives(mesh, shapes=True, noIntermediate=True) or []
        if shapes:
            mesh_shape = shapes[0]
        else:
            mesh_shape = mesh

        # -- Get history (deformers only)
        history = mref.listHistory(mesh_shape, pruneDagObjects=True) or []

        blendshapes = mref.ls(history, type="blendShape") or mref.ReferenceList()
        skinclusters = mref.ls(history, type="skinCluster") or mref.ReferenceList()

        if not blendshapes:
            return []

        # -- If skinned, reorder so skinCluster evaluates after blendShape
        # -- (prevents popping when deleting)
        for bs in blendshapes:
            for sc in skinclusters:
                try:
                    mref.reorderDeformers(sc, bs, mesh_shape)
                except RuntimeError:
                    pass

        # -- Delete blendShapes
        mref.delete(blendshapes)

        return blendshapes


class LinkBlendshapes(aniseed.RigComponent):
    """
    Drives the weights of the driven blendshapes from the matching (by alias)
    weights of the driving blendshape.
    """

    identifier = "TPS : Link BlendShapes"

    def __init__(self, *args, **kwargs):
        """
        Declares the driving blendshape input and the list of driven
        blendshapes input.
        """
        aniseed.RigComponent.__init__(self, *args, **kwargs)

        self.declare_input(
            name="Driving Blendshape",
            value="",
        )

        self.declare_input(
            name="Driven Blendshapes",
            value=[],
        )

    def input_widget(self, requirement_name: str):
        """
        Returns an object list for the driven blendshapes and an object
        selector for the driving blendshape.
        """
        if requirement_name == "Driven Blendshapes":
            return aniseed.widgets.ObjectList()
        return aniseed.widgets.ObjectSelector()

    def run(self) -> bool:
        """
        Connects each aliased weight attribute of the driving blendshape to
        the attribute of the same name on every driven blendshape. Despite the
        annotation, nothing is returned.
        """
        driving_blendshape = mref.get(
            self.input("Driving Blendshape").get(),
        )
        driven_blendshapes = mref.get(
            self.input("Driven Blendshapes").get(),
        )

        for attribute in driving_blendshape.alias_attributes():
            for driven_blendshape in driven_blendshapes:
                driven_attribute = mref.get(f"{driven_blendshape.name()}.{attribute.name()}")

                attribute.connect(driven_attribute)
