import aniseed_toolkit
import maya.cmds as mc


class CreateGuide(aniseed_toolkit.Tool):
    identifier = "Create Guide"
    classification = "Rigging"
    categories = [
        "Creation",
    ]

    # --------------------------------------------------------------------------------------
    def run(
        self,
        joint="",
        parent=None,
        position_only=False,
        shape="core_cube",
        scale=3.0,
        link_to=None,
    ) -> str:
        """
        Creates a simple guide control object to transform a joint

        Args:
            joint: The joint to drive with this guide
            parent: The parent of this guide
            position_only: If True, the joint will only be position constrained
                to the guide control
            shape: The shape of the guide control (accessible via
                aniseed_toolkit/_resources/shapes
            scale: The scale of the guide control shape
            link_to: If given, a guide line will be drawn between this node
                and the linked node

        Returns:
            Name of the guide control node
        """

        # -- Create the guide control
        guide_control = mc.rename(
            mc.createNode("transform"),
            "GDE_" + joint,
        )

        mc.addAttr(
            guide_control,
            shortName="guideLink",
            at="message",
        )

        mc.connectAttr(
            f"{joint}.message",
            f"{guide_control}.guideLink",
        )

        aniseed_toolkit.run("Apply Shape",
            node=guide_control,
            data=shape,
            color=[
                50,
                255,
                50,
            ],
            scale_by=scale,
        )

        mc.xform(
            guide_control,
            matrix=mc.xform(
                joint,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        if position_only:
            mc.pointConstraint(
                guide_control,
                joint,
                maintainOffset=False,
            )

        else:
            mc.parentConstraint(
                guide_control,
                joint,
                maintainOffset=False,
            )

        if parent:
            mc.parent(
                guide_control,
                parent,
            )

        if link_to:
            link(
                guide_control,
                link_to,
            )

        return guide_control

    @classmethod
    def link(cls, guide_a, guide_b):

        mc.select(clear=True)
        curve = mc.curve(
            d=1,
            p=[
                [0, 0, 0],
                [0, 0, 0],
            ],
        )

        mc.setAttr(
            f"{curve}.inheritsTransform",
            False,
        )

        mc.parent(
            curve,
            guide_a,
        )

        curve_shape = mc.listRelatives(curve, shapes=True)[0]

        # -- Make the curve unselectable
        mc.setAttr(
            f"{curve_shape}.template",
            True
        )

        # -- Create the first cluster
        mc.select("%s.cv[0]" % curve_shape)
        cls_root_handle, cls_root_xfo = mc.cluster()

        # -- Create the second cluster
        mc.select("%s.cv[1]" % curve)
        cls_target_handle, cls_target_xfo = mc.cluster()

        # -- Hide the clusters, as we do not want them
        # -- to be interactable
        mc.setAttr(
            f"{cls_root_xfo}.visibility",
            False,
        )

        mc.setAttr(
            f"{cls_target_xfo}.visibility",
            False,
        )

        # -- Ensure they"re both children of the guide
        mc.parent(
            cls_root_xfo,
            guide_a,
        )

        mc.parent(
            cls_target_xfo,
            guide_b,
        )

        mc.xform(
            cls_root_xfo,
            matrix=mc.xform(
                guide_a,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )

        mc.xform(
            cls_target_xfo,
            matrix=mc.xform(
                guide_b,
                query=True,
                matrix=True,
                worldSpace=True,
            ),
            worldSpace=True,
        )


class GuideTween(aniseed_toolkit.Tool):

    identifier = "Create Guide Tween"
    classification = "Rigging"
    categories = [
        "Creation",
    ]

    # --------------------------------------------------------------------------------------
    def run(self, drive_this, from_this, to_this, parent=None, factor=None):
        """
        Creates a blended constraint
        """
        tween_control = aniseed_toolkit.run(
            "Create Guide",
            drive_this,
            parent=parent,
            scale=1.5,
            shape="core_sphere",
        )

        total_distance = aniseed_toolkit.run("Distance Between",
            from_this,
            to_this,
        )

        delta = aniseed_toolkit.run(
            "Distance Between",
            drive_this,
            to_this,
        )
        distance_factor = min(1.0, delta / total_distance)

        cns = mc.pointConstraint(
            to_this,
            tween_control,
            maintainOffset=False,
        )[0]

        mc.pointConstraint(
            from_this,
            tween_control,
            maintainOffset=False,
        )

        mc.addAttr(
            tween_control,
            shortName="blend",
            at="float",
            k=True,
            dv=distance_factor,
        )

        reverse_node = mc.createNode("reverse")

        mc.connectAttr(
            f"{tween_control}.blend",
            f"{reverse_node}.inputX",
        )

        mc.connectAttr(
            f"{reverse_node}.outputX",
            cns + "." + mc.pointConstraint(
                cns,
                query=True,
                weightAliasList=True,
            )[0],
        )

        mc.connectAttr(
            f"{tween_control}.blend",
            cns + "." + mc.pointConstraint(
                cns,
                query=True,
                weightAliasList=True,
            )[-1],
        )

        for srt in ["s", "t", "r"]:
            for axis in ["x", "y", "z"]:
                mc.setAttr(
                    f"{tween_control}.{srt}{axis}",
                    lock=True,
                    k=False,
                )

