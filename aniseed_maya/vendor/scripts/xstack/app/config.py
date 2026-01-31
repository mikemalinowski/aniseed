import scribble
from . import resources


# --------------------------------------------------------------------------------------
class AppConfig:
    """
    This class allows you to tailor how the Ui Application will present itself
    to the user.

    Typically, if you inherit from the AppWidget within StackX you will find it
    useful to also subclass this config class, and use it to tailor how the ui
    is presented.
    """
    # -- These allow applications to tailor their appearance and
    # -- terminology
    label = "Stack"
    component_label = "Component"
    execute_label = "Execute"
    header_label = None
    show_tree_header = True
    splitter_bias = None # -- Percentage along the splitter should be by default
    show_menu_bar = True

    # -- These let you tailor the icons which will be displayed for various
    # -- items and actions
    icon = resources.get("icon.png")
    open_icon = resources.get("open.png")
    save_icon = resources.get("save.png")
    component_icon = resources.get("component.png")
    validate_icon = resources.get("validate.png")
    execute_icon = resources.get("execute.png")
    add_icon = resources.get("add.png")
    remove_icon = resources.get("remove.png")
    duplicate_icon = resources.get("duplicate.png")

    # -- These are how the background of the stack should show
    splash_image = resources.get("icon.png")
    stack_background = resources.get("stack_background.png")

    # -- This is the base class of the stack. This is useful if you are inheriting
    # -- and subclassing from xstack.Stack and want to ensure that when the app
    # -- creates a new stack it creates your base class
    stack_class: "xstack.Stack" = None

    # -- These allow you to tailor exactly how the tree will will visually
    item_highlight_color = [255, 0, 255]

    drop_target_width = 5
    drag_target_color = [255, 255, 255]
    default_text_color = [255, 255, 255]
    border_color = [0, 0, 0]

    status_success_color = [0, 255, 0]
    status_failed_color = [255, 0, 0]
    status_invalid_color = [255, 200, 50]
    status_unknown_color = [100, 100, 255]
    status_disabled_color = [0, 0, 0]

    text_font = "Ariel"
    text_size = 8
    item_size = 40
    component_paths = []

    # -- This lets you specify a custom application widget class
    app_widget = None

    # -- This allows you to specify a unique settings id to store settings specific
    # -- to your deployment
    settings_id = "xstack_app_settings"
    additional_settings = {}

    # ----------------------------------------------------------------------------------
    @classmethod
    def default_settings(cls):
        internal_settings = {
            "auto_adjust_orientiation": False,
            "use_vertical_alignment": True,
        }
        internal_settings.update(cls.additional_settings)
        return internal_settings

    # ----------------------------------------------------------------------------------
    @classmethod
    def get_setting(cls, key):
        return scribble.get(cls.settings_id).get(
            key,
            cls.default_settings()[key],
        )

    # ----------------------------------------------------------------------------------
    @classmethod
    def store_setting(cls, key, value):
        settings = scribble.get(cls.settings_id)
        settings[key] = value
        settings.save()


    # ----------------------------------------------------------------------------------
    @classmethod
    def all_settings(cls):
        settings = cls.default_settings()
        settings.update(scribble.get(cls.settings_id))
        return settings
