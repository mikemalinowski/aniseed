# -- Any paths defined in this environment variable will automatically be
# -- added to the components location
COMPONENT_PATHS_ENVVAR = "XSTACK_COMPONENT_PATHS"


# --------------------------------------------------------------------------------------
class Status:
    """
    This is considered an enum class for storing the state of a component
    during its execution
    """
    Failed = "failed"
    Success = "success"
    Invalid = "invalid"
    NotExecuted = "not executed"
    Disabled = "disabled"
