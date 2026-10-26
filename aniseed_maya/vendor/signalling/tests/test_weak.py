import functools
import unittest
import signalling


class LinearData1:
    Result = False


class LinearData2:
    Result = False


def flip_value_function1():
    LinearData1.Result = True


def flip_value_function2():
    LinearData2.Result = True


class ValueFlipClass:

    def flip_value_instance_method1(self):
        LinearData1.Result = True

    def flip_value_instance_method2(self):
        LinearData2.Result = True

    @classmethod
    def flip_value_classmethod1(cls):
        LinearData1.Result = True

    @classmethod
    def flip_value_classmethod2(cls):
        LinearData2.Result = True


def flip_value_partial_function(req1, req2):
    LinearData1.Result = True


class ValueFlipPartialClass:

    def flip_value_instance_method(self, req1, req2):
        LinearData1.Result = True


    @classmethod
    def flip_value_classmethod(cls, req1, req2):
        LinearData1.Result = True



class TestStandardTests(unittest.TestCase):

    def test_can_instance_signal(self):
        self.assertTrue(
            isinstance(signalling.WeakSignal(), object),
        )

    def test_emit_single_signal_function(self):

        # -- Reset the linear data
        LinearData1.Result = False

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(flip_value_function1)

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)

    def test_emit_single_signal_instance_method(self):
        # -- Reset the linear data
        LinearData1.Result = False
        instanced_class = ValueFlipClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(instanced_class.flip_value_instance_method1)

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)

    def test_emit_single_signal_classmethod(self):
        # -- Reset the linear data
        LinearData1.Result = False
        instanced_class = ValueFlipClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(instanced_class.flip_value_classmethod1)

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)

    def test_emit_multi_signal_function(self):

        # -- Reset the linear data
        LinearData1.Result = False
        LinearData2.Result = False

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(flip_value_function1)
        signal.connect(flip_value_function2)

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)
        self.assertTrue(LinearData2.Result)

    def test_emit_multi_signal_instance_method(self):
        # -- Reset the linear data
        LinearData1.Result = False
        LinearData2.Result = False
        instanced_class = ValueFlipClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(instanced_class.flip_value_instance_method1)
        signal.connect(instanced_class.flip_value_instance_method2)

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)
        self.assertTrue(LinearData2.Result)

    def test_emit_multi_signal_classmethod(self):
        # -- Reset the linear data
        LinearData1.Result = False
        LinearData2.Result = False
        instanced_class = ValueFlipClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(instanced_class.flip_value_classmethod1)
        signal.connect(instanced_class.flip_value_classmethod2)

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)
        self.assertTrue(LinearData2.Result)

    def test_emit_single_partial_signal_function(self):

        # -- Reset the linear data
        LinearData1.Result = False

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        partial = functools.partial(
            flip_value_partial_function,
            1,
            2,
        )
        signal.connect(
            partial,
        )

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)

    def test_emit_single_signal_partial_instance_method(self):
        # -- Reset the linear data
        LinearData1.Result = False
        instanced_class = ValueFlipPartialClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        partial = functools.partial(
            instanced_class.flip_value_instance_method,
            1,
            2,
        )
        signal.connect(partial)

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)

    def test_emit_single_signal_partial_classmethod(self):
        # -- Reset the linear data
        LinearData1.Result = False
        instanced_class = ValueFlipPartialClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        partial = functools.partial(
            instanced_class.flip_value_classmethod,
            1,
            2,
        )
        signal.connect(partial)

        # -- Emit the signal
        signal.emit()

        self.assertTrue(LinearData1.Result)

    def test_signal_disconnect_function(self):

        # -- Reset the linear data
        LinearData1.Result = False
        LinearData2.Result = False

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(flip_value_function1)
        signal.connect(flip_value_function2)

        # -- Now disconnect the first signal
        disconnect_result = signal.disconnect(flip_value_function1)

        # -- Emit the signal
        signal.emit()

        self.assertFalse(LinearData1.Result)
        self.assertTrue(LinearData2.Result)
        self.assertTrue(disconnect_result)

    def test_signal_disconnect_instance_method(self):

        # -- Reset the linear data
        LinearData1.Result = False
        LinearData2.Result = False

        instanced_class = ValueFlipClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(instanced_class.flip_value_instance_method1)
        signal.connect(instanced_class.flip_value_instance_method2)

        # -- Now disconnect the first signal
        disconnect_result = signal.disconnect(instanced_class.flip_value_instance_method1)

        # -- Emit the signal
        signal.emit()

        self.assertFalse(LinearData1.Result)
        self.assertTrue(LinearData2.Result)
        self.assertTrue(disconnect_result)

    def test_signal_disconnect_class_method(self):

        # -- Reset the linear data
        LinearData1.Result = False
        LinearData2.Result = False

        instanced_class = ValueFlipClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(instanced_class.flip_value_classmethod1)
        signal.connect(instanced_class.flip_value_classmethod2)

        # -- Now disconnect the first signal
        disconnect_result = signal.disconnect(instanced_class.flip_value_classmethod1)

        # -- Emit the signal
        signal.emit()

        self.assertFalse(LinearData1.Result)
        self.assertTrue(LinearData2.Result)
        self.assertTrue(disconnect_result)

    def test_signal_disconnect_all(self):

        # -- Reset the linear data
        LinearData1.Result = False
        LinearData2.Result = False

        instanced_class = ValueFlipClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(instanced_class.flip_value_classmethod1)
        signal.connect(instanced_class.flip_value_classmethod2)

        # -- Now disconnect the first signal
        disconnect_result = signal.disconnect()

        # -- Emit the signal
        signal.emit()

        self.assertFalse(LinearData1.Result)
        self.assertFalse(LinearData2.Result)
        self.assertTrue(disconnect_result)

    def test_signal_disconnect_unknown(self):

        # -- Reset the linear data
        LinearData1.Result = False
        LinearData2.Result = False

        instanced_class = ValueFlipClass()

        # -- Create a signal and connect it to a normal function call
        signal = signalling.WeakSignal()
        signal.connect(instanced_class.flip_value_classmethod1)
        signal.connect(instanced_class.flip_value_classmethod2)

        # -- Now disconnect the first signal
        disconnect_result = signal.disconnect(instanced_class)

        self.assertFalse(disconnect_result)
