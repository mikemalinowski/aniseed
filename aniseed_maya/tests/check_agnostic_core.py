"""
Checks that the core of aniseed is application agnostic.

Nothing in aniseed may import an application specific library (maya, mref,
aniseed_toolkit, ...). Application specific code belongs in an aniseed
package, such as aniseed_maya_standard. This check does three things:

    1. Imports aniseed with those libraries blocked, so any import of them
       during the import of aniseed fails.
    2. Scans the source of every core module for imports of them.
    3. Checks that, outside of an application, the standalone host is used
       and maya only packages are not.

usage: python check_agnostic_core.py <scripts_root> [<vendor_scripts_root>]
       (run with mayapy, or any python which has aniseed's vendored
       dependencies and Qt available)
"""
import os
import re
import sys
import importlib.abc

scripts_root = os.path.abspath(sys.argv[1])
vendor_root = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(scripts_root), "vendor", "scripts",
)

BLOCKED = ("maya", "mref", "aniseed_toolkit", "pymel", "OpenMaya")

blocked_attempts = []


class _Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.split(".")[0] in BLOCKED:
            # -- Record which file attempted the import
            frame = sys._getframe(1)
            while frame and (frame.f_code.co_filename.startswith("<") or "importlib" in frame.f_code.co_filename):
                frame = frame.f_back
            origin = f"{frame.f_code.co_filename}:{frame.f_lineno}" if frame else "unknown"

            # -- crosswalk is the application agnostic layer: it probes for
            # -- each application and falls back when the probe fails
            if os.sep + "crosswalk" + os.sep not in origin:
                blocked_attempts.append(f"{fullname} (from {origin})")
            raise ImportError(f"{fullname} is blocked by check_agnostic_core")
        return None


sys.meta_path.insert(0, _Blocker())
sys.path[:0] = [scripts_root, vendor_root]

failures = []

# -- 1. Import aniseed with the application libraries blocked
try:
    import aniseed
    assert aniseed.__file__.startswith(scripts_root), aniseed.__file__
except Exception as error:
    failures.append(f"importing aniseed failed: {type(error).__name__}: {error}")

if blocked_attempts:
    failures.append(f"blocked imports attempted while importing aniseed: {sorted(set(blocked_attempts))}")

# -- 2. Scan the core source for imports of application libraries
pattern = re.compile(
    r"^\s*(?:import|from)\s+(" + "|".join(BLOCKED) + r")\b",
    re.MULTILINE,
)
aniseed_root = os.path.join(scripts_root, "aniseed")

for root, folders, files in os.walk(aniseed_root):
    if "__pycache__" in root:
        continue

    for filename in files:
        if not filename.endswith(".py"):
            continue
        path = os.path.join(root, filename)
        with open(path, encoding="utf-8") as f:
            for match in pattern.finditer(f.read()):
                failures.append(f"{os.path.relpath(path, aniseed_root)} imports {match.group(1)}")

# -- 3. Outside of an application the standalone host should be used, and
# -- packages written only for maya should not contribute components. Loading
# -- the hosts attempts (and is expected to fail) to import maya, so this is
# -- done after the blocked imports have been checked.
try:
    host_name = aniseed.host.get().name
    if host_name != "standalone":
        failures.append(f"expected the standalone host, got {host_name!r}")

    for package in aniseed.packages.active():
        if package.metadata.get("hosts") == ["maya"]:
            failures.append(f"maya only package {package.name} is active outside of maya")

except Exception as error:
    failures.append(f"resolving the host and packages failed: {type(error).__name__}: {error}")

if failures:
    for failure in failures:
        print("FAIL", failure)
    print("AGNOSTIC_CHECK FAILED")
    sys.exit(1)

print("AGNOSTIC_CHECK OK")
