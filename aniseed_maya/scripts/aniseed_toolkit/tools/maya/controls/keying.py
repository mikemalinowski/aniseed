import mref
import aniseed_toolkit
import snappy
import maya
from maya import cmds


class KeyRigControls(aniseed_toolkit.Tool):

    identifier = "Key All Rig Controls"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]

    def run(self):
        """
        This will key all the controls of the currently selected rig(s). If no
        rig is selected then it will key all controls for all rigs.
        """
        cmds.setKeyframe(
            aniseed_toolkit.run(
                "Get Controls",
            ),
        )


class SnappySnap(aniseed_toolkit.Tool):
    
    identifier = "Snappy Snap"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]
    tag = "IKOnly"

    user_facing = False
    
    def run(self, nodes=None):
        # -- Get the groups for all the nodes
        groups = []
        nodes = nodes or cmds.ls(selection=True)
        for node in nodes:
            groups.extend(snappy.groups(node))
        groups = list(set(groups))

        start_time = None
        end_time = None

        if mref.time.selected_number_of_frames() > 1:
            start_time = mref.time.selected_start_frame()
            end_time = mref.time.selected_end_frame()

        for group in groups:
            if self.tag in group:
                snappy.snap(
                    group=group,
                    start_time=start_time,
                    end_time=end_time,
                )


class SnapIKOnly(SnappySnap):
    identifier = "Snap Ik To Fk (Selected Limb)"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]
    tag = "IKOnly"
    user_facing = True



class SnapFKOnly(SnappySnap):
    identifier = "Snap Fk To Ik (Selected Limb)"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]
    tag = "FKOnly"
    user_facing = True


class SnapIKFKBasedOnSlider(aniseed_toolkit.Tool):
    identifier = "Switch IKFK (Selected Limb)"
    classification = "Animation"
    categories = [
        "Keys",
        "Controls",
    ]
    tag = "IKOnly"

    def run(self, nodes=None):

        # -- Get the selection
        nodes = nodes or cmds.ls(selection=True)

        # -- Get the namespace
        namespace = ""
        if ":" in nodes[0]:
            namespace = nodes[0].split(":")[0] + ":"

        # -- Get the groups for all the nodes
        groups = []
        for node in nodes:
            groups.extend(snappy.groups(node))
        groups = list(set(groups))

        # -- Extract the ikfk group
        ikfk_group = None
        for group in groups:
            if "IKFK" in group:
                ikfk_group = group

        if not ikfk_group:
            print("Could not find an ikfk group")
            return

        # -- Get the ikfk attribute and value
        ikfk_attribute = snappy.get_data(ikfk_group, "ikfk_attribute")
        ikfk_value = cmds.getAttr(f"{namespace}{ikfk_attribute}")

        if ikfk_value > 0.001:
            # -- Switch to ik
            print("switching to ik")
            SnapIKOnly().run(nodes=nodes)
            cmds.setAttr(f"{namespace}{ikfk_attribute}", 0.0)
        else:
            # -- Switch to fk
            print("switching to fk")
            SnapFKOnly().run(nodes=nodes)
            cmds.setAttr(f"{namespace}{ikfk_attribute}", 1.0)


# class SnapIKFKInRig(aniseed_toolkit.Tool):
#     identifier = "Snap IKFK (All In Rig)"
#     classification = "Animation"
#     categories = [
#         "Keys",
#         "Controls",
#     ]
#
#     def run(self, namespace=None):
#
#         if not namespace and cmds.ls(selection=True):
#             namespace = cmds.ls(selection=True)[0].split(":")[0]
#
#         if not namespace:
#             return
#
#         start_time = None
#         end_time = None
#         if mref.time.selected_number_of_frames() > 1:
#             start_time = mref.time.selected_start_frame()
#             end_time = mref.time.selected_end_frame()
#
#         # -- Get the groups for all the nodes
#         for group in snappy.groups_in_namespace(namespace):
#             if "IKFK" in group:
#                 snappy.snap(
#                     group=group,
#                     start_time=start_time,
#                     end_time=end_time,
#                 )
#
