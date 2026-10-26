"""
Widgets used by the dev examples. Any widget returned from option_widget or
input_widget must provide:

    * a ``changed`` signal, emitted whenever the user changes the value
    * ``get_value()``, returning a json serialisable value
    * ``set_value(value)``, showing the given value

See components/05_extending/ex12_custom_widget.py for a worked example.
"""
from .slider_spin_box import SliderSpinBox
from .folder_selector import FolderSelector
