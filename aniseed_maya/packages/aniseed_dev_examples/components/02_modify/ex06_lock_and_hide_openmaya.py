"""
Provides the "Dev Example : Lock And Hide (OpenMaya)" component, which locks
and hides attributes on existing nodes, using only maya.api.OpenMaya.

What this example teaches:
    * Finding a node and its plugs with MSelectionList, MFnDependencyNode
      and MPlug
    * Handling compound attributes, such as translate
    * Why changes made through OpenMaya are not undoable

Compare with: ex05_colour_nodes_cmds.py, a modifier written with maya.cmds.

Read next: ../03_create/ex07_joint_chain_cmds.py
"""
import typing
import logging

# -- OpenMaya 2.0 (maya.api) is the only Maya API this example uses. Prefer it
# -- to the older maya.OpenMaya: it is more pythonic and faster.
from maya.api import OpenMaya as om

import aniseed

log = logging.getLogger(__name__)


class LockAndHideOpenMaya(aniseed.RigComponent):
    """
    Locks the given attributes on the given nodes, and optionally hides them
    from the channel box. Compound attributes such as translate are locked
    along with all of their children.
    """

    identifier = "Dev Example : Lock And Hide (OpenMaya)"

    # -- Key idea: OpenMaya changes bypass Maya's undo queue. Only changes made
    # -- through commands (maya.cmds, or an MPxCommand in a plugin) can be
    # -- undone. The app wraps the whole build in one undo step, so undoing a
    # -- build undoes everything the cmds components did, but NOT what this
    # -- component did. The locks stay until something unlocks them.
    # --
    # -- That makes OpenMaya the right choice for reading the scene quickly,
    # -- or for work which is rebuilt every time anyway, and maya.cmds the
    # -- right choice when a user might want to undo the change.

    def __init__(self, *args, **kwargs):
        """
        Declares the Nodes input and the Attributes, Lock and Hide options.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Nodes",
            value=[],
            description="The nodes whose attributes should be locked",
            group="Scene",
        )

        self.declare_option(
            name="Attributes",
            value=["translate", "rotate", "scale", "visibility"],
            description="The attributes to lock. Compound attributes lock their children too.",
            group="Behaviour",
            pre_expose=True,
        )

        self.declare_option(
            name="Lock",
            value=True,
            description="If on the attributes are locked, if off they are unlocked",
            group="Behaviour",
        )

        self.declare_option(
            name="Hide",
            value=True,
            description="If on the attributes are also hidden from the channel box",
            group="Behaviour",
        )

    def option_widget(self, option_name):
        """
        Returns a text list for the Attributes option.
        """
        if option_name == "Attributes":
            return aniseed.widgets.TextList()
        return None

    def input_widget(self, requirement_name):
        """
        Returns an object list for the Nodes input.
        """
        if requirement_name == "Nodes":
            return aniseed.widgets.ObjectList()
        return None

    def run(self):
        """
        Locks (or unlocks) each attribute on each node, hiding it when Hide
        is on. Attributes a node does not have are skipped with a warning.
        """
        nodes = self.input("Nodes").get()

        # -- A wired input may hold a single node name rather than a list
        if isinstance(nodes, str):
            nodes = [nodes]

        lock = self.option("Lock").get()
        hide = self.option("Hide").get()

        for node_name in nodes:

            # -- MFnDependencyNode is a "function set": a set of functions
            # -- which work on whichever node (MObject) it is given
            node_fn = om.MFnDependencyNode(_get_node(node_name))

            for attribute_name in self.option("Attributes").get():

                if not node_fn.hasAttribute(attribute_name):
                    log.warning(f"{self.label()} : {node_name} has no {attribute_name} attribute")
                    continue

                # -- False means we want the attribute's plug itself, rather
                # -- than one of the plugs Maya keeps for its connections
                plug = node_fn.findPlug(attribute_name, False)

                for each_plug in _plug_and_children(plug):
                    each_plug.isLocked = lock

                    # -- A compound parent such as translate is never shown
                    # -- in the channel box itself, only its children are
                    if hide and not each_plug.isCompound:
                        each_plug.isKeyable = False
                        each_plug.isChannelBox = False

        return True


def _get_node(node_name: str) -> om.MObject:
    """
    Returns the MObject of the node with the given name.

    MSelectionList is the usual way to turn a name into an MObject. Adding a
    name which does not exist raises a RuntimeError, so we raise a clearer
    error of our own instead.

    Args:
        node_name: The name of the node.
    """
    selection = om.MSelectionList()

    try:
        selection.add(node_name)

    except RuntimeError:
        raise ValueError(f"{node_name!r} does not exist in the scene") from None

    return selection.getDependNode(0)


def _plug_and_children(plug: om.MPlug) -> typing.List[om.MPlug]:
    """
    Returns the plug, followed by its children if it is a compound plug (such
    as translate, whose children are translateX, translateY and translateZ).

    Args:
        plug: The plug to expand.
    """
    plugs = [plug]

    if plug.isCompound:
        plugs.extend(plug.child(index) for index in range(plug.numChildren()))

    return plugs
