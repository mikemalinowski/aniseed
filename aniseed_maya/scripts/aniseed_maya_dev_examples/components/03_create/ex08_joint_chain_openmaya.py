"""
Provides the "Dev Example : Joint Chain (OpenMaya)" component, which creates
an evenly spaced joint chain between two nodes, using only maya.api.OpenMaya.

What this example teaches:
    * Creating nodes with an MDagModifier
    * Building an orientation from vectors, and applying it as a joint orient
    * Converting API objects into plain names for outputs

Compare with: ex07_joint_chain_cmds.py. The inputs, options and outputs are
identical, so diff the two files to see where the APIs differ. For a straight
chain, both produce the same joints.

Read next: ex09_simple_control.py
"""
import logging

# -- OpenMaya 2.0 is the only Maya API this example uses
from maya.api import OpenMaya as om

import aniseed

log = logging.getLogger(__name__)


class JointChainOpenMaya(aniseed.RigComponent):
    """
    Creates a chain of joints spaced evenly from the Start node to the End
    node. Each joint's X axis aims down the chain, with Y pointing up.
    """

    identifier = "Dev Example : Joint Chain (OpenMaya)"

    def __init__(self, *args, **kwargs):
        """
        Declares the Parent, Start and End inputs, the naming and joint count
        options, and the Root Joint, Tip Joint and Joints outputs. These are
        the same as in ex07_joint_chain_cmds.py.
        """
        super().__init__(*args, **kwargs)

        self.declare_input(
            name="Parent",
            value="",
            description="The node the chain is parented under. If empty, the chain is left in the world.",
            validate=False,
            group="Scene",
        )

        self.declare_input(
            name="Start",
            value="",
            description="The node marking where the chain starts",
            group="Scene",
        )

        self.declare_input(
            name="End",
            value="",
            description="The node marking where the chain ends",
            group="Scene",
        )

        self.declare_option(
            name="Description",
            value="chain",
            description="Used when naming the joints",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Location",
            value=self.config.middle,
            description="The location (side) token used when naming the joints",
            group="Naming",
            pre_expose=True,
        )

        self.declare_option(
            name="Joint Count",
            value=4,
            description="How many joints to create, including the start and end joints",
            group="Behaviour",
            pre_expose=True,
        )

        self.declare_output(
            name="Root Joint",
            description="The first joint in the chain",
            is_default=True,
        )
        self.declare_output(
            name="Tip Joint",
            description="The last joint in the chain",
        )
        self.declare_output(
            name="Joints",
            description="Every joint in the chain, from root to tip",
        )

    def option_widget(self, option_name):
        """
        Returns a location selector for Location and a limited spin box for
        Joint Count.
        """
        if option_name == "Location":
            return aniseed.widgets.LocationSelector(
                self.config,
                value=self.option("Location").get(),
            )

        if option_name == "Joint Count":
            return aniseed.widgets.LimitedInteger(minimum=2, maximum=50)

        return None

    def input_widget(self, requirement_name):
        """
        Returns an object selector for the Parent, Start and End inputs.
        """
        if requirement_name in ("Parent", "Start", "End"):
            return aniseed.widgets.ObjectSelector(component=self)
        return None

    def is_valid(self) -> bool:
        """
        Checks the Start, End and Parent nodes exist (when they are not wired
        to another component) and that there are at least two joints.
        """
        for input_name in ("Parent", "Start", "End"):
            node_input = self.input(input_name)

            if node_input.is_address() or not node_input.get():
                continue

            # -- The OpenMaya way to check a name exists: try to find it
            if _find_dag_path(node_input.get()) is None:
                log.warning(f"{self.label()} : {input_name} {node_input.get()!r} does not exist")
                return False

        if self.option("Joint Count").get() < 2:
            log.warning(f"{self.label()} : Joint Count must be at least 2")
            return False

        return True

    def run(self):
        """
        Creates the joints, names them, positions and orients them, and fills
        in the outputs.
        """
        count = self.option("Joint Count").get()

        # -- MFnTransform reads and writes transforms. kWorld asks for the
        # -- world space position, the equivalent of xform(worldSpace=True).
        start = om.MFnTransform(_find_dag_path(self.input("Start").get())).translation(om.MSpace.kWorld)
        end = om.MFnTransform(_find_dag_path(self.input("End").get())).translation(om.MSpace.kWorld)

        # -- MVector supports maths directly: subtraction, length, normal
        chain_vector = end - start
        if chain_vector.length() < 1e-6:
            raise ValueError(f"{self.label()} : Start and End are in the same place")

        segment_length = chain_vector.length() / (count - 1)

        # -- Work out where the chain will live. A null MObject means the world.
        parent_name = self.input("Parent").get()
        parent_object = om.MObject.kNullObj
        parent_inverse = om.MMatrix()  # -- the identity matrix

        if parent_name:
            parent_path = _find_dag_path(parent_name)
            parent_object = parent_path.node()
            parent_inverse = parent_path.inclusiveMatrixInverse()

        # -- Key idea: an MDagModifier queues up changes and applies them all
        # -- at once when doIt is called. Each joint is created under the
        # -- previous one, which is how the chain is formed.
        modifier = om.MDagModifier()
        joint_objects = []
        create_under = parent_object

        for _ in range(count):
            joint_object = modifier.createNode("joint", create_under)
            joint_objects.append(joint_object)
            create_under = joint_object

        modifier.doIt()

        # -- Name the joints once they exist. The configuration checks the
        # -- scene for clashes, so each name has to be applied before the next
        # -- one is generated, otherwise every joint would be given the _01 name.
        for joint_object in joint_objects:
            om.MFnDependencyNode(joint_object).setName(
                self.config.generate_name(
                    classification=self.config.joint,
                    description=self.option("Description").get(),
                    location=self.option("Location").get(),
                ),
            )

        # -- The root joint's world orientation, as a matrix whose rows are
        # -- the X, Y and Z axes followed by the position. The matrix is
        # -- relative to the world, so multiply it by the parent's inverse
        # -- matrix to make it relative to the parent.
        world_matrix = _aim_matrix(chain_vector, start)
        local_matrix = om.MTransformationMatrix(world_matrix * parent_inverse)

        for index, joint_object in enumerate(joint_objects):

            # -- MFnTransform works on any transform, joints included
            transform_fn = om.MFnTransform(joint_object)

            if index == 0:
                # -- The root sits at the start, oriented down the chain.
                # -- As with cmds.joint, the orientation goes on the joint
                # -- orient, leaving rotate at zero for animators.
                transform_fn.setTranslation(local_matrix.translation(om.MSpace.kTransform), om.MSpace.kTransform)
                _set_joint_orient(transform_fn, local_matrix.rotation())

            else:
                # -- Every other joint is one segment along its parent's X
                # -- axis, with the same orientation as its parent
                transform_fn.setTranslation(om.MVector(segment_length, 0, 0), om.MSpace.kTransform)

        # -- Outputs must be plain values. MObjects and MDagPaths cannot be
        # -- saved in a recipe, and they stop being valid when the scene
        # -- changes, so convert them to names. partialPathName gives the
        # -- shortest unique name, the same as maya.cmds returns.
        joint_names = [om.MFnDagNode(joint_object).partialPathName() for joint_object in joint_objects]

        self.output("Root Joint").set(joint_names[0])
        self.output("Tip Joint").set(joint_names[-1])
        self.output("Joints").set(joint_names)

        log.info(f"{self.label()} created {len(joint_names)} joints")
        return True

    # -- A comparison with ex07_joint_chain_cmds.py:
    # --   * cmds is shorter, and cmds.joint(orientJoint=...) does the
    # --     orientation maths for us, where here we build it ourselves
    # --   * OpenMaya is much faster when creating or reading many nodes
    # --   * the cmds version can be undone, but this one cannot
    # --     (see ex06_lock_and_hide_openmaya.py)
    # -- For a handful of joints, prefer cmds. Reach for OpenMaya when speed
    # -- matters, or when you need something cmds does not offer.


def _find_dag_path(node_name: str):
    """
    Returns the MDagPath of the node with the given name, or None if there is
    no such node.

    Args:
        node_name: The name of the node.
    """
    selection = om.MSelectionList()

    try:
        selection.add(node_name)

    except RuntimeError:
        return None

    return selection.getDagPath(0)


def _aim_matrix(aim: om.MVector, position: om.MVector) -> om.MMatrix:
    """
    Returns a matrix at the given position whose X axis points along the aim
    vector and whose Y axis points as close to world up as it can.

    Args:
        aim: The direction the X axis should point.
        position: Where the matrix should be.
    """
    x_axis = aim.normal()

    # -- If the chain points straight up, world up cannot be used to find the
    # -- other axes, so fall back to world Z
    up = om.MVector(0, 1, 0)
    if abs(x_axis * up) > 0.999:
        up = om.MVector(0, 0, 1)

    # -- ^ is the cross product. Crossing two vectors gives a third which is
    # -- perpendicular to both.
    z_axis = (x_axis ^ up).normal()
    y_axis = z_axis ^ x_axis

    return om.MMatrix(
        [
            x_axis.x, x_axis.y, x_axis.z, 0,
            y_axis.x, y_axis.y, y_axis.z, 0,
            z_axis.x, z_axis.y, z_axis.z, 0,
            position.x, position.y, position.z, 1,
        ]
    )


def _set_joint_orient(transform_fn: om.MFnTransform, rotation: om.MEulerRotation) -> None:
    """
    Sets the joint orient of a joint. MFnTransform has no joint orient
    function (that is in OpenMayaAnim's MFnIkJoint), so the jointOrient plugs
    are set directly.

    Args:
        transform_fn: A function set for the joint.
        rotation: The orientation to apply, in radians.
    """
    for axis, value in zip("XYZ", (rotation.x, rotation.y, rotation.z)):
        transform_fn.findPlug(f"jointOrient{axis}", False).setMAngle(om.MAngle(value))
