"""
Helpers for driving transforms directly from matrices.
"""
import mref


def drive_from_local_matrix(driver, driven) -> mref.ReferencedItem:
    """
    Drives the translate, rotate and scale of the driven transform from
    the local matrix of the driver (via a decomposeMatrix node). This makes
    the driven node mimic the local transform of the driver.

    Args:
        driver: The transform whose local matrix should be read
        driven: The transform to drive

    Returns:
        The decomposeMatrix node
    """
    driver = mref.get(driver)
    driven = mref.get(driven)

    decompose_node = mref.create("decomposeMatrix")
    driver.attr("matrix").connect(decompose_node.inputMatrix)
    decompose_node.outputTranslate.connect(driven.attr("translate"))
    decompose_node.outputRotate.connect(driven.attr("rotate"))
    decompose_node.outputScale.connect(driven.attr("scale"))

    return decompose_node
