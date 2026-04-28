import mref
import aniseed
import aniseed_toolkit


# noinspection PyUnresolvedReferences
class BlendshapeFacialRig(aniseed.RigComponent):

    identifier = "TPS : BlendShape Based Facial Rig"

    left = "left"
    right = "right"

    sides = [
        "left",
        "right",
    ]

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
        super(BlendshapeFacialRig, self).__init__(*args, **kwargs)

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

        for control_label in self.control_groups:
            group = "Control : %s" % control_label.replace("_", " ").title()

            self.declare_option(
                name=f"{control_label}_control",
                value="",
                group=group,
            )
            self.declare_option(
                name=f"{control_label}_parent",
                value="",
                group=group,
            )

            self.declare_option(
                name=f"{control_label}_guide",
                value="",
                group=group,
            )

            self.declare_option(
                name=f"{control_label}_shape",
                value="core_cube",
                group=group,
            )


    def input_widget(self, requirement_name: str):
        return aniseed.widgets.ObjectSelector()

    def option_widget(self, requirement_name: str):
        if requirement_name.endswith("_shape"):
            return aniseed.widgets.ShapeSelector(default_item="core_cube")

        return aniseed.widgets.ObjectSelector()

    def run(self):
        base_mesh = mref.get(self.input("Base Mesh").get())
        
        self.remove_blendshapes(base_mesh)

        attribute_dictionary = self.setup_blendshape(base_mesh)
        addition_nodes = self.initialise_driving_adds(attribute_dictionary)

        for key, value in attribute_dictionary.items():
            print(f"{key}: {value}")

        self.setup_lip_puller(
            location="left",
            guide=self.option("left_lip_corner_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_lip_puller(
            location="right",
            guide=self.option("right_lip_corner_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_central_lip(
            section="upper",
            guide=self.option("upper_lip_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )
        self.setup_central_lip(
            section="lower",
            guide=self.option("lower_lip_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_nose(
            guide=self.option("nose_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_inner_brow(
            location="left",
            guide=self.option("left_brow_inner_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_inner_brow(
            location="right",
            guide=self.option("right_brow_inner_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_outer_brow(
            location="left",
            guide=self.option("left_brow_outer_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )

        self.setup_outer_brow(
            location="right",
            guide=self.option("right_brow_outer_guide").get(),
            parent=self.input("Parent").get(),
            connection_map=addition_nodes,
        )


    def setup_blendshape(self, base_mesh: mref.ReferencedItem):
        attribute_dictionary = dict()
        targets = []
        input_names = []

        for shape in self.shape_list:
            input_name = f"{shape}"
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
        for idx, input_name in enumerate(input_names):
            attribute_dictionary[input_name] = blendshape_node.attr(f"weight[{idx}]")
        return attribute_dictionary

    def setup_outer_brow(self, location, guide, parent, connection_map):
        control = self.resolve_control(
            description="brow_outer",
            identity_label=f"{location}_brow_outer",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tx", "tz"],
        )

        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_outer_up"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_outer_down"],
        )

        self.expose_direct(
            control=control,
            label="squint_inner",
            destination_attribute=connection_map[f"{location}_squint_inner"],
        )

        self.expose_direct(
            control=control,
            label="squint_outer",
            destination_attribute=connection_map[f"{location}_squint_outer"],
        )


    def setup_inner_brow(self, location, guide, parent, connection_map):

        control = self.resolve_control(
            description="brow_inner",
            identity_label=f"{location}_brow_inner",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tz"],
        )
        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_inner_up"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_brow_inner_down"],
        )
        self.clamped_reversal(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_brow_inner_in"],
            clamp_min=-1,
        )

        self.expose_direct(
            control=control,
            label="mid_brow",
            destination_attribute=connection_map[f"{location}_brow_mid_up"]
        )
        self.expose_reversal_direct(
            control=control,
            label="mid_brow",
            destination_attribute=connection_map[f"{location}_brow_mid_down"]
        )

    def setup_nose(self, guide, parent, connection_map, scale=1):

        control = self.resolve_control(
            description="nose",
            identity_label="nose",
            location=self.config.middle,
            parent=parent,
            guide=guide,
        )

        self.expose_direct(
            control=control,
            label=f"left_nose_flare",
            destination_attribute=connection_map[f"left_nose_flare"]
        )
        self.expose_direct(
            control=control,
            label=f"right_nose_flare",
            destination_attribute=connection_map[f"right_nose_flare"]
        )

    def setup_central_lip(self, section, guide, parent, connection_map):

        control = self.resolve_control(
            description=f"{section}_lip",
            identity_label=f"{section}_lip",
            location=self.config.middle,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tx"],
        )

        self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{section}_lip_pull"],
        )

        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{section}_lip_compress"],
        )

        self.clamped_connection(
            driving_attribute=control.attr("translateZ"),
            destination_attribute=connection_map[f"{section}_lip_curl_out"],
        )

        self.clamped_reversal(
            driving_attribute=control.attr("translateZ"),
            destination_attribute=connection_map[f"{section}_lip_curl_in"],
        )
        self.expose_direct(
            control=control,
            label=f"right_sneer",
            destination_attribute=connection_map[f"right_lip_sneer_{section}"],
            clamp_min=-1,
        )
        self.expose_direct(
            control=control,
            label=f"left_sneer",
            destination_attribute=connection_map[f"left_lip_sneer_{section}"],
            clamp_min=-1,
        )

        # -- Set up the sneering fixer
        add_sneers = mref.create("floatMath")
        control.attr("right_sneer").connect(add_sneers.attr("floatA"))
        control.attr("left_sneer").connect(add_sneers.attr("floatB"))

        divide_by_two = mref.create("floatMath")
        divide_by_two.attr("operation").set(2)  # -- Multiply
        divide_by_two.attr("floatB").set(0.5)
        add_sneers.attr("outFloat").connect(divide_by_two.attr("floatA"))

        add_direct = mref.create("floatMath")
        divide_by_two.attr("outFloat").connect(add_direct.attr("floatA"))

        self.expose_direct(
            control=control,
            label="sneer_fixup",
            destination_attribute=add_direct.attr("floatB"),
            clamp_min=-1,
            clamp_max=1,
            do_next=False,
        )
        clamp = mref.create("clamp")
        clamp.attr("minR").set(-1)
        clamp.attr("maxR").set(1)
        add_direct.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(connection_map[f"{section}_sneer"])

    def setup_lip_puller(self, location, guide, parent, connection_map):

        control = self.resolve_control(
            description=f"lip_puller",
            identity_label=f"{location}_lip_corner",
            location=location,
            parent=parent,
            guide=guide,
            lock_and_hide=["sx", "sy", "sz", "rx", "ry", "rz", "tz"],
        )

        # -- Pull Out Behaviour
        self.clamped_connection(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_out"],
        )

        # -- Push In Behaviour
        self.clamped_reversal(
            driving_attribute=control.attr("translateX"),
            destination_attribute=connection_map[f"{location}_lip_corner_push_in"],
        )

        # -- Pull Down In Behaviour
        self.clamped_reversal(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_down"],
        )

        # -- Push Up Behaviour
        corner_pull_up_setup = self.clamped_connection(
            driving_attribute=control.attr("translateY"),
            destination_attribute=connection_map[f"{location}_lip_corner_pull_up"],
        )

        # -- Now add the squint
        remap_node = mref.create("remapValue")
        corner_pull_up_setup["clamp"].attr("outputR").connect(remap_node.attr("inputValue"))
        remap_node.attr("inputMax").set(1)
        remap_node.attr("value[0].value_Position").set(0.25)
        remap_node.attr("value[0].value_FloatValue").set(0)
        remap_node.attr("value[0].value_Interp").set(2) # Smooth
        remap_node.attr("value[1].value_Position").set(1)
        remap_node.attr("value[1].value_FloatValue").set(0.25)
        remap_node.attr("outValue").connect_next(connection_map[f"{location}_squint_outer"])

        # -- Set up our direct connections
        self.expose_direct(
            control=control,
            label="Blow",
            destination_attribute=connection_map[f"{location}_cheek_blow"],
        )
        self.expose_reversal_direct(
            control=control,
            label="Blow",
            destination_attribute=connection_map[f"{location}_cheek_suck"],
        )

    def initialise_driving_adds(self, attribute_dictionary):

        driving_additions = dict()

        for label, attribute in attribute_dictionary.items():
            node = mref.create("plusMinusAverage")
            node.attr("output1D").connect(attribute)

            driving_additions[label] = node.attr("input1D")
        return driving_additions

    @staticmethod
    def remove_blendshapes(mesh: mref.ReferencedItem):
        """
        Remove all blendShape nodes from a mesh while preserving skinning.
    
        Args:
            mesh (str): transform or shape
    
        Returns:
            list[str]: removed blendShape nodes
        """
    
        # Get shape if transform passed
        shapes = mref.listRelatives(mesh, shapes=True, noIntermediate=True) or []
        if shapes:
            mesh_shape = shapes[0]
        else:
            mesh_shape = mesh
    
        # Get history (deformers only)
        history = mref.listHistory(mesh_shape, pruneDagObjects=True) or []
    
        blendshapes = mref.ls(history, type="blendShape") or mref.ReferenceList()
        skinclusters = mref.ls(history, type="skinCluster") or mref.ReferenceList()
    
        if not blendshapes:
            return []
    
        # If skinned, reorder so skinCluster evaluates after blendShape
        # (prevents popping when deleting)
        for bs in blendshapes:
            for sc in skinclusters:
                try:
                    mref.reorderDeformers(sc, bs, mesh_shape)
                except RuntimeError:
                    pass
    
        # Delete blendShapes
        mref.delete(blendshapes)
    
        return blendshapes

    def clamped_connection(self, driving_attribute, destination_attribute, clamp_min=0, clamp_max=1):

        clamp = mref.create("clamp")
        clamp.attr(f"maxR").set(clamp_max)
        clamp.attr(f"minR").set(clamp_min)
        driving_attribute.connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

        return {
            "clamp": clamp,
        }

    def clamped_reversal(self, driving_attribute, destination_attribute, clamp_min=0, clamp_max=1):

        # -- Push In Behaviour
        clamp = mref.create("clamp")
        inverse = mref.create("floatMath")
        inverse.attr("operation").set(2) # -- Multiply
        inverse.attr("floatB").set(-1)
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)
        driving_attribute.connect(inverse.attr("floatA"))
        inverse.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

        return {
            "clamp": clamp,
            "multiplier": inverse,
        }

    def expose_reversal_direct(self, control: mref.ReferencedItem, label, destination_attribute, clamp_min=0, clamp_max=1):

        if control.has_attribute(label):
            attribute = control.attr(label)
        else:
            attribute = control.add_attribute(
                label,
                value=0,
                attribute_type="float",
                keyable=True,
            )
        clamp = mref.create("clamp")
        inverse = mref.create("floatMath")

        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)

        inverse.attr("operation").set(2) # -- Multiply
        inverse.attr("floatB").set(-1)

        attribute.connect(inverse.attr("floatA"))
        inverse.attr("outFloat").connect(clamp.attr("inputR"))
        clamp.attr("outputR").connect_next(destination_attribute)

    def expose_direct(self, control: mref.ReferencedItem, label, destination_attribute, clamp_min=0, clamp_max=1, do_next=True):

        if control.has_attribute(label):
            attribute = control.attr(label)
        else:
            attribute = control.add_attribute(
                label,
                value=0,
                attribute_type="float",
                keyable=True,
            )
        clamp = mref.create("clamp")
        clamp.attr("maxR").set(clamp_max)
        clamp.attr("minR").set(clamp_min)
        attribute.connect(clamp.attr("inputR"))

        if do_next:
            clamp.attr("outputR").connect_next(destination_attribute)
        else:
            clamp.attr("outputR").connect(destination_attribute)

        return {
            "clamp": clamp,
        }

    def resolve_control(self, description, identity_label, location, parent, guide, lock_and_hide=None):
        control_name = self.option(f"{identity_label}_control").get()
        if control_name:
            return mref.get(control_name)#, aniseed_toolkit.control.Control(control_name)

        new_control_setup = aniseed_toolkit.control.create(
            description=description,
            location=location,
            parent=self.option(f"{identity_label}_parent").get() or parent,
            shape=self.option(f"{identity_label}_shape").get() or "core_cube",
            config=self.config,
            match_to=guide or None,
        )

        if lock_and_hide:
            aniseed_toolkit.attributes.lock_and_hide([new_control_setup.ctl], lock_and_hide, lock=True, hide=True)

        # -- Start by creating the control
        return mref.get(new_control_setup.ctl)#, new_control_setup


class LinkBlendshapes(aniseed.RigComponent):

    identifier = "TPS : Link BlendShapes"

    def __init__(self, *args, **kwargs):
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
        if requirement_name == "Driven Blendshapes":
            return aniseed.widgets.ObjectList()
        return aniseed.widgets.ObjectSelector()

    def run(self) -> bool:
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