import weakref


class WeakSignal:
    """
    Generalised signal class which allows for signals to be connected to
    and triggered when emitted.
    """

    def __init__(self):
        self._callables = list()

    def connect(self, method):
        try:
            self._callables.append(weakref.WeakMethod(method))
        except TypeError:
            self._callables.append(weakref.ref(method))

    def disconnect(self, socket: callable = None):

        if not socket:
            self._callables.clear()
            return True

        for entry in self._callables:
            if entry() == socket:
                self._callables.remove(entry)
                return True

        return False

    def emit(self, *args, **kwargs):
        for method_ref in self._callables:
            if method_ref():
                method_ref()(*args, **kwargs)
