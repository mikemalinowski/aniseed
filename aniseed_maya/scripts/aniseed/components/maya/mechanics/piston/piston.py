import aniseed
import aniseed_toolkit
import maya.cmds as mc


class PistonComponent(aniseed.RigComponent):

    identifier = "Mechanics : Piston"

    def __init__(self, *args, **kwargs):
        super(PistonComponent, self).__init__(*args, **kwargs)

        self.declare_input(
            name="Base Parent",
            value="",
            group="Control Rig"
        )

        self.declare_input(
            name="Tip Parent",
            value="",
            group="Control Rig"
        )

        self.declare_input(
            name="Base Joint",
            value="",
            group="Joint Requirements",
        )

        self.declare_input(
            name="Tip Joint",
            value="",
            group="Joint Requirements",
        )

        self.declare_option(
            name="Descriptive Prefix",
            value="",
            group="Naming",
        )

        self.declare_option(
            name="Location",
            value="md",
            group="Naming",
            should_inherit=True,
            pre_expose=True,
        )

        self.declare_output(name="Root")
        self.declare_output(name="Tip")

    def input_widget(self, requirement_name: str):

        object_requirements = [
            "Base Parent",
            "Tip Parent",
            "Base Joint",
            "Tip Joint",
        ]

        if requirement_name in object_requirements:
            return aniseed.widgets.ObjectSelector(component=self)

    def option_widget(self, option_name: str):
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(self.config)

    def run(self) -> bool:

        base_parent = self.input("Base Parent").get()
        tip_parent = self.input("Tip Parent").get()

        piston_root_jnt = self.input("Base Joint").get()
        piston_tip_jnt = self.input("Tip Joint").get()

        prefix = self.option("Descriptive Prefix").get()
        location = self.option("Location").get()

        piston_root_ctl = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}PistonTip",
            location=location,
            config=self.config,
            parent=base_parent,
            shape="core_cube",
            match_to=piston_root_jnt,
        )

        piston_tip_ctl = aniseed_toolkit.run(
            "Create Control",
            description=f"{prefix}PistonTip",
            location=location,
            config=self.config,
            parent=tip_parent,
            shape="core_cube",
            match_to=piston_tip_jnt,
        )

        aim_root = self._create_node(
            classification="piv",
            description=f"{prefix}PistonRootAim",
            parent=piston_root_ctl.ctl,
            match_to=piston_root_ctl.ctl,
        )

        aim_tip = self._create_node(
            classification="piv",
            description=f"{prefix}PistonTipAim",
            parent=piston_tip_ctl.ctl,
            match_to=piston_tip_ctl.ctl,
        )

        upvector = self._create_node(
            classification="upv",
            description=f"{prefix}PistonUpVector",
            parent=piston_root_ctl.ctl,
            match_to=piston_root_ctl.ctl,
        )

        mc.setAttr(
            f"{upvector}.translateZ",
            10,
        )

        mc.aimConstraint(
            piston_tip_ctl.ctl,
            aim_root,
            aimVector=[0, 1, 0],
            upVector=[1, 0, 0],
            worldUpType="object",
            worldUpObject=upvector,
            maintainOffset=False,
        )

        mc.aimConstraint(
            piston_root_ctl.ctl,
            aim_tip,
            aimVector=[0, 1, 0],
            upVector=[1, 0, 0],
            worldUpType="object",
            worldUpObject=upvector,
            maintainOffset=False,
        )

        mc.parentConstraint(
            aim_root,
            piston_root_jnt,
            maintainOffset=True,
        )

        mc.parentConstraint(
            aim_tip,
            piston_tip_jnt,
            maintainOffset=True,
        )

        self.output("Root").set(aim_root)
        self.output("Tip").set(aim_tip)

        return True

    def _create_node(self, classification, description, parent, match_to):

        node = mc.rename(
            mc.createNode("transform"),
            self.config.generate_name(
                classification=classification,
                description=description,
                location=self.option("Location").get(),
            ),
        )

        mc.xform(
            node,
            matrix=mc.xform(
                match_to,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        mc.parent(
            node,
            parent,
        )

        return node
