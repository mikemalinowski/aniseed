import typing
import xstack
import webbrowser


# --------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class RigComponent(xstack.Component):
    """
    Aniseed components should all inherit from this Rig Component. The only
    difference between a RigComponent and a xstack Component is that the rig
    is always accessible via .rig and the configuration component is always
    accessible from the .config property.
    """
    help_url = ""

    # ----------------------------------------------------------------------------------
    # This MUST be re-implemented
    def run(self) -> bool:
        """
        This should be re-implemented in your component and should contain all the
        code which you want to trigger during the build.
        """
        return True

    # ----------------------------------------------------------------------------------
    # You may re-implement this
    def is_valid(self) -> bool:
        """
        You can use this to test the validation of the options and requirements.
        """
        return True

    # ----------------------------------------------------------------------------------
    # You may re-implement this
    def option_widget(self, option_name: str) -> "PySide6.QWidget":
        """
        This allows you to return a specific (or custom) QWidget to represent the
        given option in any ui's.

        This requires Qt, which is optional.

        For example, your code here might look like this:

        ```
        if option_name == "foobar":
            return QtWidgets.QLineEdit()
        ```
        """
        return None

    # ----------------------------------------------------------------------------------
    # You may re-implement this
    def input_widget(self, requirement_name: str) -> "PySide6.QWidget":
        """
        This allows you to return a specific (or custom) QWidget to represent the
        given requirement in any ui's.

        This requires Qt, which is optional.

        For example, your code here might look like this:

        ```
        if requirement_name == "foobar":
            return QtWidgets.QLineEdit()
        ```
        """
        return None

    # ----------------------------------------------------------------------------------
    # You may re-implement this
    def user_functions(self) -> typing.Dict[str, callable]:
        """
        This should return a dictionary where the key is a label/identifier for the
        functionality and the value is a callable function. These are typically exposed
        to the user through the front end tool. This allows you to provide the user
        with additional features beyond just building the component.
        """
        return {}

    # ----------------------------------------------------------------------------------
    @property
    def rig(self) -> "aniseed_everywhere.Rig":
        """
        Returns the Rig Instance this component belongs to

        :return:
        """
        return self.stack

    # ----------------------------------------------------------------------------------
    @property
    def config(self):
        """
        Returns the configuration component that is defined in the stack

        :return:
        """
        return self.rig.config()

    # ----------------------------------------------------------------------------------
    def help(self):
        """
        The default rig config behaviour is to open a help url. But any config can
        freely re-implement this function to implement any method of help they require
        """
        if self.help_url:
            webbrowser.open(self.help_url)

    # ----------------------------------------------------------------------------------
    def suggested_label(self):
        """
        This allows a component to declare a default label for a component. Typically
        a user will be able to change this, but it gives a good starting point.
        """

        label = self.identifier.title().split(":")[-1].strip()

        if self.option("Location") and self.config:

            location = self.option("Location").get()
            if location and location != self.config.middle:
                label = f"{label} {location.upper()}"

        return label
