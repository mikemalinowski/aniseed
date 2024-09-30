import typing


# ------------------------------------------------------------------------------
class Signal(object):
    """
    A simple signal emission mechanism to allow for events within functions
    to trigger mid-call callbacks.
    """

    # --------------------------------------------------------------------------
    def __init__(self):
        self._callables: typing.List[callable] = list()

    # --------------------------------------------------------------------------
    def connect(self, item: callable):
        self._callables.append(item)

    # --------------------------------------------------------------------------
    def emit(self, *args, **kwargs):
        for item in self._callables:
            item(*args, **kwargs)

    # ----------------------------------------------------------------------------------
    def disconnect(self, socket: callable = None):

        if not socket:
            self._callables.clear()
            return True

        if socket in self._callables:
            self._callables.remove(socket)
            return True

        return False
