"""
Small helpers for building node based maths networks. Each helper creates
its node(s) and returns the address of the output plug, so calls can be
nested to build up expressions, e.g. ``add(multiply(a, b), c)``.

Terms can be either an attribute address (str) or a plain number, in which
case the value is set on the input rather than connected.
"""
import mref


# -- floatMath operation indices
ADD = 0


SUBTRACT = 1


MULTIPLY = 2


DIVIDE = 3


def _float_math(first_term, second_term, operation=ADD) -> str:
    node = mref.create("floatMath")
    node.operation.set(operation)

    for term, plug in ((first_term, node.floatA), (second_term, node.floatB)):
        if isinstance(term, str):
            mref.get(term).connect(plug)
        else:
            plug.set(term)

    return node.outFloat.full_name()


def add(first_term, second_term) -> str:
    return _float_math(first_term, second_term, ADD)


def subtract(first_term, second_term) -> str:
    return _float_math(first_term, second_term, SUBTRACT)


def multiply(first_term, second_term) -> str:
    return _float_math(first_term, second_term, MULTIPLY)


def divide(first_term, second_term) -> str:
    return _float_math(first_term, second_term, DIVIDE)


def exp(first_term: str) -> str:
    """
    floatMath has no exponent operation, so an expression drives floatA
    """
    node = mref.create("floatMath")
    node.floatB.set(0)
    mref.expression(s=f"{node.floatA.full_name()}=exp({first_term})")
    return node.outFloat.full_name()


def matrix_to_translate(matrix_attr: str) -> str:
    node = mref.create("decomposeMatrix")
    mref.get(matrix_attr).connect(node.inputMatrix)
    return node.outputTranslate.full_name()


def subtract_vector(first_term: str, second_term: str) -> str:
    node = mref.create("colorMath")
    mref.get(first_term).connect(node.colorA)
    mref.get(second_term).connect(node.colorB)
    node.operation.set(SUBTRACT)
    return node.outColor.full_name()


def length(first_term: str, second_term: str) -> str:
    """
    Returns the distance between two vector (translate) plugs
    """
    delta_attr = subtract_vector(first_term, second_term)

    node = mref.create("length")
    mref.get(delta_attr).connect(node.attr("input"))
    return node.attr("output").full_name()
