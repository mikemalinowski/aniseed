"""
Helpers for components which declare a dynamic number of outputs.

They only call methods on the component they are given, so the toolkit does not
need to import aniseed.
"""
from ..scene import joints as _joints


def clear_outputs(component, prefix: str) -> None:
    """
    Removes every output on the component whose name starts with the
    given prefix.

    Args:
        component: The component to remove the outputs from
        prefix: The prefix of the output names to remove
    """
    for output in list(component.outputs()):
        if output.name().startswith(prefix):
            component.remove_output(output.name())


def declare_joint_outputs(component, prefix: str, root_joint: str, tip_joint: str) -> None:
    """
    Rebuilds the outputs of a component which has one output per joint
    in a chain. All outputs starting with the prefix are removed and then
    an output named "<prefix> <index>" is declared for each joint between
    the root and the tip.

    If the joints cannot be resolved (for instance one of the inputs is
    blank) then no outputs are declared.

    Args:
        component: The component to declare the outputs on
        prefix: The prefix of the output names, e.g. "FK Control"
        root_joint: The first joint in the chain
        tip_joint: The last joint in the chain
    """
    clear_outputs(component, prefix)

    # -- It's possible one or both of the joints are blank or missing, in
    # -- which case there are no joints to represent.
    try:
        joint_count = len(_joints.get_between(root_joint, tip_joint))
    except Exception:
        joint_count = 0

    for idx in range(joint_count):
        component.declare_output(name=f"{prefix} {idx}")
