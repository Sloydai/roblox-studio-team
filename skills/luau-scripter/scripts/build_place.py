#!/usr/bin/env python3
"""Build the Roblox place file from the Rojo project. Downloads Rojo itself if it isn't installed.

  python3 <skills>/luau-scripter/scripts/build_place.py              # builds roblox-game/SloydGame.rbxlx
  python3 <skills>/luau-scripter/scripts/build_place.py my-game      # another project folder

If the project folder doesn't exist yet, it's created from the bundled template first.
Standard library only. Rojo comes from its official GitHub release (pinned below) and is
kept next to this script, so nothing is installed system-wide.
"""

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile

ROJO_VERSION = "7.7.1"
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(os.path.dirname(HERE), "templates", "rojo-game")
TOOLS = os.path.join(os.path.dirname(HERE), ".tools", f"rojo-{ROJO_VERSION}")


def rojo_asset():
    system = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(platform.system())
    machine = platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "x86_64"
    if not system:
        sys.exit(f"No Rojo download for {platform.system()}. Install Rojo yourself: https://rojo.space")
    return f"rojo-{ROJO_VERSION}-{system}-{arch}.zip"


def find_rojo():
    on_path = shutil.which("rojo")
    if on_path:
        return on_path
    exe = os.path.join(TOOLS, "rojo.exe" if os.name == "nt" else "rojo")
    if os.path.isfile(exe):
        return exe
    asset = rojo_asset()
    url = f"https://github.com/rojo-rbx/rojo/releases/download/v{ROJO_VERSION}/{asset}"
    print(f"Rojo isn't installed. Downloading Rojo {ROJO_VERSION} (one time only)...", flush=True)
    os.makedirs(TOOLS, exist_ok=True)
    archive = os.path.join(TOOLS, asset)
    try:
        with urllib.request.urlopen(url, timeout=300) as resp, open(archive, "wb") as out:
            shutil.copyfileobj(resp, out)
    except OSError as err:
        sys.exit(f"Couldn't download Rojo ({err}). Check your internet connection, or install Rojo: https://rojo.space")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(TOOLS)
    os.remove(archive)
    if os.name != "nt":
        os.chmod(exe, os.stat(exe).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return exe


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project", nargs="?", default="roblox-game", help="Rojo project folder (default roblox-game)")
    p.add_argument("--out", default="SloydGame.rbxlx", help="Place file name, written inside the project folder")
    args = p.parse_args()

    project = os.path.abspath(args.project)
    if not os.path.isdir(project):
        shutil.copytree(TEMPLATE, project)
        print(f"Created {project} from the template.")
    if not os.path.isfile(os.path.join(project, "default.project.json")):
        sys.exit(f"{project} has no default.project.json. Is this the right folder?")

    rojo = find_rojo()
    proc = subprocess.run([rojo, "build", "default.project.json", "-o", args.out], cwd=project,
                          capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.exit("Rojo build failed:\n" + proc.stderr)
    print(f"\nDone. Open this file in Roblox Studio: {os.path.join(project, args.out)}")


if __name__ == "__main__":
    main()
