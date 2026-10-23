# -- When in studio environments, the developers may want to keep their
# -- own component code in a separate location to open source code. To
# -- make this achievable we expose an environment variable which we will
# -- always look at for paths to find components within.
RIG_COMPONENTS_PATHS_ENVVAR = "ANISEED_RIG_COMPONENT_PATHS"

# -- Aniseed packages are folders which contribute components, mixins,
# -- widgets and hosts. By default we look alongside the aniseed module,
# -- but this environment variable allows any number of additional
# -- packages (or folders of packages) to be declared.
ANISEED_PACKAGE_PATHS_ENVVAR = "ANISEED_PACKAGE_PATHS"

website = "https://github.com/mikemalinowski/aniseed"

# -- The version of aniseed. This is stored in every recipe.
VERSION = "4.0.0"