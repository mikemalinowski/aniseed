from .. import control
from .. import math

import maya.cmds as mc


# --------------------------------------------------------------------------------------
class TwistSetup:

    def __init__(self, twist_count, description, location, config):

        # -- Store our incoming variables
        self._twist_count = twist_count
        self._description = description
        self._location = location
        self._config = config

        # -- Store out outgoing variables
        self._org = None
        self._root = None
        self._root_control = None
        self._tip = None
        self._tip_control = None
        self._twists = list()

    # ----------------------------------------------------------------------------------
    def org(self):
        return self._org

    # ----------------------------------------------------------------------------------
    def root(self):
        return control.get_classification(
            self._root_control,
            "org",
        )

    # ----------------------------------------------------------------------------------
    def tip(self):
        return control.get_classification(
            self._tip_control,
            "org",
        )

    # ----------------------------------------------------------------------------------
    def twists(self):
        return [
            t["twist"]
            for t in self._twists
        ]

    # ----------------------------------------------------------------------------------
    def all_controls(self):
        control_nodes = self.twists()
        control_nodes.append(self._root_control)
        control_nodes.append(self._tip_control)

        return control_nodes

    # ----------------------------------------------------------------------------------
    def reset_aim(self):

        vector = math.direction_between(
            self._root,
            self._tip,
        )

        for t in self._twists:
            mc.setAttr(
                f"{t['aim_node']}.primaryInputAxisX",
                vector.x,
            )

            mc.setAttr(
                f"{t['aim_node']}.primaryInputAxisY",
                vector.y,
            )

            mc.setAttr(
                f"{t['aim_node']}.primaryInputAxisZ",
                vector.z,
            )

    # ----------------------------------------------------------------------------------
    def set_blend_factor(self, twist_index, blend_factor):
        blend_factor = max(
            0.001,
            min(
                0.9999,
                blend_factor,
            )
        )

        mc.setAttr(
            f"{self._twists[twist_index]['blend_node']}.target[1].weight",
            blend_factor,
        )

    # ----------------------------------------------------------------------------------
    def build(self):

        self._org = mc.rename(
            mc.createNode("transform"),
            self._config.generate_name(
                classification="org",
                description=self._description + "TwistGroup",
                location=self._location,
            ),
        )

        self._root_control = control.create(
            description=f"{self._description}Root",
            location=self._location,
            parent=self._org,
            shape="core_paddle",
            shape_scale=8.0,
            config=self._config,
        )

        self._tip_control = control.create(
            description=f"{self._description}Tip",
            location=self._location,
            parent=self._org,
            shape="core_paddle",
            shape_scale=8.0,
            config=self._config,
        )

        self._root = mc.rename(
            mc.createNode("transform"),
            self._config.generate_name(
                classification="mech",
                description=self._description + "Root",
                location=self._location,
            ),
        )
        self._tip = mc.rename(
            mc.createNode("transform"),
            self._config.generate_name(
                classification="mech",
                description=self._description + "Tip",
                location=self._location,
            ),
        )

        mc.parent(
            self._root,
            self._org
        )

        mc.parent(
            self._tip,
            self._org,
        )

        mc.parentConstraint(
            self._root_control,
            self._root,
        )

        mc.parentConstraint(
            self._tip_control,
            self._tip,
        )

        for idx in range(self._twist_count):

            blend_factor = max(
                0.001,
                min(
                    0.9999,
                    idx / (self._twist_count - 1)
                )
            )

            twist = control.create(
                description=f"{self._description}Twister",
                location=self._location,
                parent=self._org,
                shape="core_paddle",
                shape_scale=4,
                config=self._config,
            )

            twist_org = control.get_classification(
                twist,
                "org",
            )

            blend_matrix = mc.createNode("blendMatrix")

            mc.connectAttr(
                f"{self._root}.matrix",
                f"{blend_matrix}.target[0].targetMatrix",
            )

            mc.connectAttr(
                f"{self._tip}.matrix",
                f"{blend_matrix}.target[1].targetMatrix",
            )

            decompose_matrix = mc.rename(
                mc.createNode("decomposeMatrix"),
            )

            aim_matrix = mc.rename(
                mc.createNode("aimMatrix"),
                "aimMatrix",
            )

            mc.connectAttr(
                f"{blend_matrix}.outputMatrix",
                f"{aim_matrix}.inputMatrix",
            )

            mc.connectAttr(
                f"{self._tip}.matrix",
                f"{aim_matrix}.primary.primaryTargetMatrix",
            )

            mc.connectAttr(
                f"{aim_matrix}.outputMatrix",
                f"{decompose_matrix}.inputMatrix"
            )

            mc.connectAttr(
                f"{decompose_matrix}.outputTranslate",
                f"{twist_org}.translate",
            )

            mc.connectAttr(
                f"{decompose_matrix}.outputRotate",
                f"{twist_org}.rotate",
            )

            mc.setAttr(
                f"{blend_matrix}.target[1].weight",
                blend_factor,
            )

            self._twists.append(
                dict(
                    twist=twist,
                    blend_node=blend_matrix,
                    aim_node=aim_matrix,
                )
            )