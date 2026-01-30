import xstack

class MinimalComponent(xstack.Component):
    """
    The most basic style of component. No options, no requirements.
    """
    identifier = "MinimalComponent"

    def __init__(self, *args, **kwargs):
        super(MinimalComponent, self).__init__(*args, **kwargs)

    def run(self):
        return True

class VersionedComponent1(xstack.Component):
    """
    The most basic style of component. No options, no requirements.
    """
    identifier = "Versioned Component"
    version = 1

    def __init__(self, *args, **kwargs):
        super(VersionedComponent1, self).__init__(*args, **kwargs)

    def run(self):
        print("Running Version " + str(self.version))
        return True


class VersionedComponent2(xstack.Component):
    """
    The most basic style of component. No options, no requirements.
    """
    identifier = "Versioned Component"
    version = 2

    def __init__(self, *args, **kwargs):
        super(VersionedComponent2, self).__init__(*args, **kwargs)

    def run(self):
        print("Running Version " + str(self.version))
        return True


class VersionedComponent3(xstack.Component):
    """
    The most basic style of component. No options, no requirements.
    """
    identifier = "Versioned Component"
    version = 3

    def __init__(self, *args, **kwargs):
        super(VersionedComponent3, self).__init__(*args, **kwargs)

    def run(self):
        print("Running Version " + str(self.version))
        return True


class FailingComponent(xstack.Component):
    """
    This component is designed to fail during a build
    """

    identifier = "FailingComponent"

    def __init__(self, *args, **kwargs):
        super(FailingComponent, self).__init__(*args, **kwargs)

    def run(self):
        raise Exception("Enforced Failure")


class ComponentWithExpectedRequirementSet(xstack.Component):
    """
    This has one expected requirement
    """
    identifier = "ComponentWithExpectedRequirementSet"

    def __init__(self, *args, **kwargs):
        super(ComponentWithExpectedRequirementSet, self).__init__(*args, **kwargs)

        self.declare_input(
            name="expected_requirement",
            value=1,
        )

class ComponentWithExpectedRequirementNotSet(xstack.Component):
    identifier = "ComponentWithExpectedRequirementNotSet"

    def __init__(self, *args, **kwargs):
        super(ComponentWithExpectedRequirementNotSet, self).__init__(*args, **kwargs)

        self.declare_input(
            name="expected_requirement",
            value="",
            validate=True,
        )


class ComponentWithOption(xstack.Component):
    identifier = "ComponentWithOption"

    def __init__(self, *args, **kwargs):
        super(ComponentWithOption, self).__init__(*args, **kwargs)

        self.declare_option(
            name="test_option",
            value="foo",
        )

    def run(self):
        return self.option("test_option").get() == "bar"

class ComponentWithPreExposeOption(xstack.Component):
    identifier = "ComponentWithPreExposeOption"

    def __init__(self, *args, **kwargs):
        super(ComponentWithPreExposeOption, self).__init__(*args, **kwargs)

        self.declare_option(
            name="test_option",
            value="foo",
            pre_expose=True,
        )

    def suggested_label(self):
        return self.identifier + " : " + self.option("test_option").get()
    def run(self):
        return self.option("test_option").get() == "bar"

class InvalidComponent(xstack.Component):
    identifier = "InvalidComponent"

    def is_valid(self) -> bool:
        return False

class RunTestComponent(xstack.Component):

    identifier = "RunTestComponent"

    RUN_ORDER = []

    def run(self) -> bool:
        RunTestComponent.RUN_ORDER.append(self)

        return True


class ComponentWithTenOptions(xstack.Component):

    identifier = "ComponentWithTenOptions"

    RUN_ORDER = []

    def __init__(self, *args, **kwargs):
        super(ComponentWithTenOptions, self).__init__(*args, **kwargs)

        for i in range(10):
            self.declare_option(
                name=f"test_option{i}",
                value="foo",
            )

    def run(self) -> bool:
        RunTestComponent.RUN_ORDER.append(self)

        return True


class ComponentWithOutputs(xstack.Component):

    identifier = "ComponentWithOutputs"

    RUN_ORDER = []

    def __init__(self, *args, **kwargs):
        super(ComponentWithOutputs, self).__init__(*args, **kwargs)

        for i in range(3):
            self.declare_output(
                name=f"test_output{i}",
            )

    def run(self) -> bool:
        RunTestComponent.RUN_ORDER.append(self)

        self.output("test_output0").set("A")
        self.output("test_output1").set("B")
        self.output("test_output2").set("C")
        return True