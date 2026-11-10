#!/usr/bin/env python3
"""Check everything the Roblox Studio Team needs, and say exactly how to fix what's missing.

  python3 <skills>/roblox-producer/scripts/check_setup.py      (Windows: python instead of python3)

Run it from your game project folder. Standard library only. Prints nothing secret.
"""

import os
import platform
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
TEAM = ["roblox-producer", "game-designer", "prop-modeler", "skin-variants", "world-backdrop",
        "luau-scripter", "studio-importer", "sloyd-api"]
PY = "python" if os.name == "nt" else "python3"

results = []


def report(ok, name, detail, fix=None, required=True):
    tag = "[ok]     " if ok else ("[missing]" if required else "[optional]")
    print(f"{tag} {name}: {detail}")
    if not ok and fix:
        print(f"           -> {fix}")
    results.append(ok or not required)


def check_python():
    v = sys.version_info
    report(v >= (3, 9), "Python", f"{v.major}.{v.minor}.{v.micro}",
           "Install Python 3.9 or newer from https://www.python.org/downloads/")


def check_skills():
    missing = [t for t in TEAM if not os.path.isfile(os.path.join(SKILLS, t, "SKILL.md"))]
    report(not missing, "Skills", f"all 8 in {SKILLS}" if not missing else f"missing {', '.join(missing)}",
           "Reinstall: npx skills add Sloydai/roblox-studio-team --all")


def check_key():
    sys.path.insert(0, os.path.join(SKILLS, "sloyd-api", "scripts"))
    try:
        import sloyd
    except ImportError:
        report(False, "Sloyd API key", "sloyd-api skill not found", "Reinstall the skills (see above)")
        return
    sloyd.load_dotenv()
    if not (os.environ.get("SLOYD_CLIENT_ID") and os.environ.get("SLOYD_CLIENT_SECRET")):
        report(False, "Sloyd API key", "not set up in this folder",
               f"Run: {PY} {os.path.join(SKILLS, 'sloyd-api', 'scripts', 'sloyd.py')} setup")
        return
    try:
        have = sloyd.balance()
    except sloyd.SloydError as err:
        if err.status == 401:
            report(False, "Sloyd API key", "Sloyd rejected it",
                   f"Run setup again with a working key: {PY} {os.path.join(SKILLS, 'sloyd-api', 'scripts', 'sloyd.py')} setup")
        else:
            report(False, "Sloyd API key", f"couldn't reach Sloyd ({err})", "Check your internet connection and try again")
        return
    except OSError as err:
        report(False, "Sloyd API key", f"couldn't reach Sloyd ({err})", "Check your internet connection and try again")
        return
    report(True, "Sloyd API key", "works")
    report(have >= 25, "Sloyd credits", f"{have} (a small game needs about 250)",
           "Buy credits: https://api-dashboard.sloyd.ai -> Usage & Billing (minimum $12 = 900 credits)")


def check_blender():
    sys.path.insert(0, os.path.join(SKILLS, "prop-modeler", "scripts"))
    try:
        import roblox_mesh
        path = roblox_mesh.find_blender()
    except SystemExit:
        report(False, "Blender", "not found",
               "Install Blender (free) from https://www.blender.org/download/ , then run this check again")
        return
    except ImportError:
        report(False, "Blender", "prop-modeler skill not found", "Reinstall the skills (see above)")
        return
    try:
        out = subprocess.run([path, "-b", "--factory-startup", "--version"], capture_output=True, text=True,
                             timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired) as err:
        report(False, "Blender", f"found at {path} but it didn't start ({err})",
               "Reinstall Blender from https://www.blender.org/download/")
        return
    m = re.search(r"Blender (\d+)\.(\d+)", out)
    version = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    report(version >= (3, 6), "Blender", f"{version[0]}.{version[1]} at {path}",
           "Install Blender 3.6 or newer from https://www.blender.org/download/")


def check_rojo():
    path = shutil.which("rojo")
    if not path:
        report(True, "Rojo", "not installed, that's fine: the skills download it when they build your game")
        return
    out = subprocess.run([path, "--version"], capture_output=True, text=True).stdout.strip()
    report(True, "Rojo", out)


def main():
    print(f"Roblox Studio Team setup check ({platform.system()}, folder: {os.getcwd()})\n")
    check_python()
    check_skills()
    check_key()
    check_blender()
    check_rojo()
    print()
    if all(results):
        print("All set. Start your agent in this folder and ask it to build your game.")
        return 0
    print("Fix the [missing] lines above, then run this check again.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
