from PySide6 import QtGui


# --------------------------------------------------------------------------
def grayscaled(pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
    """
    Creates a new pixmap which is a grayscale version of the given
    pixmap

    Args:
        pixmap: QPixmap source

    Returns:
        A grayscale pixmap
    """
    # -- Get an image object
    image: QtGui.QImage = pixmap.toImage()

    # -- Cycle the pixels and convert them to grayscale
    for x in range(image.width()):
        for y in range(image.height()):

            # -- Grayscale the pixel
            gray = QtGui.qGray(
                image.pixel(
                    x,
                    y,
                ),
            )

            # -- Set the pixel back into the image
            image.setPixel(
                x,
                y,
                QtGui.QColor(
                    gray,
                    gray,
                    gray,
                ).rgb()
            )

    # -- Re-apply the alpha channel
    image.setAlphaChannel(
        pixmap.toImage().alphaChannel()
    )

    # -- Return the pixmap
    return QtGui.QPixmap.fromImage(image)
