import maya.cmds as mc


# --------------------------------------------------------------------------------------
def apply(node, r=0, g=0, b=0):

    rgb = [r, g, b]

    for shape in mc.listRelatives(node, shapes=True) or list():

        mc.setAttr(f"{shape}.overrideEnabled", True)
        mc.setAttr(f"{shape}.overrideRGBColors", True)
        mc.setAttr(f"{shape}.useOutlinerColor", True)

        for idx, channel in enumerate(["R", "G", "B"]):
            mc.setAttr(f"{shape}.overrideColor{channel}", rgb[idx] / 255.0)
            mc.setAttr(f"{shape}.outlinerColor{channel}", rgb[idx] / 255.0)
