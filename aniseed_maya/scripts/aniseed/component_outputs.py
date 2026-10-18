"""
Helpers for components which declare a dynamic number of outputs.
"""


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


def declare_joint_outputs(component, prefix: str, joints: list) -> None:
    """
    Rebuilds the outputs of a component which has one output per joint
    in a chain. All outputs starting with the prefix are removed and then
    an output named "<prefix> <index>" is declared for each joint.

    Args:
        component: The component to declare the outputs on
        prefix: The prefix of the output names, e.g. "FK Control"
        joints: The joints in the chain. Pass an empty list if the chain
            cannot be resolved, in which case no outputs are declared.
    """
    clear_outputs(component, prefix)

    for idx in range(len(joints or [])):
        component.declare_output(name=f"{prefix} {idx}")
