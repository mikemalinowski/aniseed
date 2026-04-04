from maya import cmds
from maya import mel


def active_start_frame() -> int:
    """
    Returns the active start frame of the scene as an integer
    :return:
    """
    return int(cmds.playbackOptions(query=True, minTime=True))


def active_end_frame() -> int:
    """
    Returns the active end frame of the scene as an integer
    :return:
    """
    return int(cmds.playbackOptions(query=True, maxTime=True))


def scope_start_frame() -> int:
    """
    Retrieves the start frame of the scene as an integer
    """
    return int(cmds.playbackOptions(query=True, animationStartTime=True))


def scope_end_frame() -> int:
    """
    Retrieves the start frame of the scene as an integer
    """
    return int(cmds.playbackOptions(query=True, animationEndTime=True))

def selected_start_frame() -> int:
    """
    Returns the start frame of the selected area. If no area is selected
    then this will return the active start frame.
    """
    return selected_frame_range()[0]

def selected_end_frame() -> int:
    """
    Returns the end frame of the selected area. If no area is selected
    then this will return the active end frame.
    """
    return selected_frame_range()[-1]

def selected_frame_range() -> list[int]:
    """
    This will return the frame range selected in the time line.
    """
    # -- Sadly we have to resort to mel to get the global playback slider
    playback_slider = mel.eval("string $tmp = $gPlayBackSlider;")
    time_range = cmds.timeControl(playback_slider, query=True, rangeArray=True)

    return [
        int(time_range[0]),
        int(time_range[1]),
    ]

def selected_number_of_frames():
    frame_range = selected_frame_range()
    return (frame_range[1] - frame_range[0])
