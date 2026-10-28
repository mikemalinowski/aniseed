+ Aniseed 1.0.0 ./aniseed_maya
ANISEED_LOCATION:=
ANISEED_PACKAGE_PATHS+:=packages
MAYA_SCRIPT_PATH+:=scripts
MAYA_SCRIPT_PATH+:=vendor
scripts: scripts
PYTHONPATH+:=vendor
PYTHONPATH+:=packages