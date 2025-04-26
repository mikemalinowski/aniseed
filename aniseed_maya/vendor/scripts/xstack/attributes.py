import typing
import signalling

from . import address


# --------------------------------------------------------------------------------------
class _Attribute:
    """
    This represents an exposed attribute to a component. Typically, an option allows
    a component to tailor its build to the specific needs and expectations of the user
    """

    # ----------------------------------------------------------------------------------
    def __init__(
            self,
            name: str,
            value: typing.Any = None,
            description: str = "",
            group: str = "",
            should_inherit: bool = False,
            pre_expose: bool = False,
            hidden: bool = False,
            component=None,
    ):
        super(_Attribute, self).__init__()

        self._name: str = name
        self._value: typing.Any = value
        self._description: str = description
        self._group: str = group
        self._should_inherit: bool = should_inherit
        self._component = component
        self._pre_expose: bool = pre_expose
        self._hidden: bool = hidden

        # -- Declare our signals which allow events to tie into them
        self.value_changed = signalling.Signal()

    # ----------------------------------------------------------------------------------
    def name(self) -> str:
        """
        Returns the name of the option
        """
        return self._name

    # ----------------------------------------------------------------------------------
    def description(self) -> str:
        """
        Returns the description of the option
        """
        return self._description

    # ----------------------------------------------------------------------------------
    def group(self):
        """
        Returns the group this node should result within
        """
        return self._group

    # ----------------------------------------------------------------------------------
    def set(self, value: typing.Any):
        """
        Sets the value of the option and emits a change event call
        """
        self._value = value
        self.value_changed.emit()

    # ----------------------------------------------------------------------------------
    def get(self, resolved=True) -> typing.Any:
        """
        Returns the value of the option
        """
        # -- If we're set as an address, return the value of the attribute
        # -- we are pointing to rather than the address
        if resolved and address.is_address(self._value):
            return address.get_attribute(self._value, self.component().stack).get()

        return self._value

    # ----------------------------------------------------------------------------------
    def should_pre_expose(self) -> bool:
        return self._pre_expose

    # ----------------------------------------------------------------------------------
    def should_inherit(self):
        """
        Sets the value of the option and emits a change event call
        """
        return self._should_inherit

    # ----------------------------------------------------------------------------------
    def serialise(self):
        """
        Serialises the option down to a json serialisable dictionary
        """
        return dict(
            name=self.name(),
            value=self.get(resolved=False),
        )

    # ----------------------------------------------------------------------------------
    def component(self):
        return self._component

    # ----------------------------------------------------------------------------------
    def is_address(self):
        if address.is_address(self._value):
            return True

    # ----------------------------------------------------------------------------------
    def hidden(self):
        return self._hidden


# --------------------------------------------------------------------------------------
class Option(_Attribute):

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(Option, self).__init__(*args, **kwargs)

    # ----------------------------------------------------------------------------------
    def address(self):
        return address.form_address(
            self,
            "option",
        )

# --------------------------------------------------------------------------------------
class Input(_Attribute):

    # ----------------------------------------------------------------------------------
    def __init__(self, validate, *args, **kwargs):
        super(Input, self).__init__(*args, **kwargs)

        self._validate = validate

    # ----------------------------------------------------------------------------------
    def requires_validation(self) -> bool:
        """
        Returns true if this requirement requires validation
        """
        return self._validate

    # ----------------------------------------------------------------------------------
    def validate(self) -> bool:
        """
        Return whether this requirement has hard requirement to be fulfilled
        """
        if self.get(resolved=False):
            return True
        return False

    # ----------------------------------------------------------------------------------
    def address(self):
        return address.form_address(
            self,
            "requirement",
        )

# --------------------------------------------------------------------------------------
class Output(_Attribute):

    # ----------------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(Output, self).__init__(*args, **kwargs)

    # ----------------------------------------------------------------------------------
    def address(self):
        return address.form_address(
            self,
            "output",
        )
