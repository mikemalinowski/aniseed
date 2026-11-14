"""
The data shared by the "Face : Lip Smoothing" component and the "Limb :
Modular Face" component which wires it up: which lip controls are smoothed,
what each follows, and the names of their inputs.
"""

SIDES = ["left", "right"]

# -- Each lip control, what its proxy is constrained to and the space it is
# -- blended from, with the weights of the two. Each row is applied to the
# -- left and then the right control (in that order, as it decides node
# -- names). "jaw", "upper_lip", "lower_lip" and "space" are the component's
# -- inputs (see DRIVER_INPUTS).
SMOOTHING = [
    ("upper_lip_outer", "jaw", "upper_lip", [0.6, 0.4]),
    ("lower_lip_outer", "lower_lip", "space", [0.4, 0.6]),
    ("upper_lip_mid", "jaw", "upper_lip", [0.8, 0.2]),
    ("lower_lip_mid", "lower_lip", "space", [0.2, 0.8]),
    ("upper_lip_inner", "jaw", "upper_lip", [1, 0]),
    ("lower_lip_inner", "lower_lip", "space", [0, 1]),
    ("dimple", "jaw", "space", [0.5, 0.5]),
]

DRIVER_INPUTS = {
    "jaw": "Jaw Control",
    "upper_lip": "Upper Lip Control",
    "lower_lip": "Lower Lip Control",
    "space": "Space",
}


def lip_input_name(label: str, side: str) -> str:
    """
    Returns the name of the input holding the given lip control
    (upper_lip_outer and left give "Upper Lip Outer Left Control")
    """
    return f"{label.replace('_', ' ').title()} {side.title()} Control"
