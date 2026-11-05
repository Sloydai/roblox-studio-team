#!/usr/bin/env python3
"""Fit Sloyd models to Roblox's MeshPart limits and export them for the 3D Importer.

Python 3.9+ standard library only. Uses Blender (3.6+, run headless) for the mesh work,
because its collapse decimator keeps UVs and seams intact.

  roblox_mesh.py check   model.glb                       # pass/fail against Roblox limits
  roblox_mesh.py process model.glb --name GumdropPlatform --height-studs 4
  roblox_mesh.py batch   roblox-assets/manifest.json     # every asset prop-modeler generated
  roblox_mesh.py preview model.glb --out preview.png     # PNG still for review or posts

Limits (Roblox creator docs, art/modeling/specifications):
  - 20,000 triangles per mesh (each MeshPart)
  - 4096 x 4096 maximum texture size; Roblox recommends ~256 px for 5-stud objects,
    512 for 10, 1024 for 20. `--max-texture auto` (default) applies that guidance.

Blender is found via --blender, $BLENDER, `blender` on PATH, or the default install paths.
Exit code 0 = everything within limits, 1 = a limit is exceeded or an error happened.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.join(HERE, "blender_roblox.py")
RESULT_PREFIX = "ROBLOX_RESULT="

ROBLOX_MAX_TRIANGLES = 20000
ROBLOX_MAX_TEXTURE = 4096
# Default decimation target leaves headroom under the hard limit.
DEFAULT_TARGET = 18000

BLENDER_CANDIDATES = {
    "Darwin": ["/Applications/Blender.app/Contents/MacOS/Blender"],
    "Windows": [
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Blender Foundation", v, "blender.exe")
        for v in ("Blender 4.5", "Blender 4.4", "Blender 4.3", "Blender 4.2", "Blender 4.1", "Blender 4.0", "Blender 3.6")
    ],
    "Linux": ["/usr/bin/blender", "/snap/bin/blender", "/opt/blender/blender"],
}


def find_blender(explicit=None):
    for candidate in [explicit, os.environ.get("BLENDER"), shutil.which("blender")]:
        if candidate and os.path.isfile(candidate):
            return candidate
    for candidate in BLENDER_CANDIDATES.get(platform.system(), []):
        if os.path.isfile(candidate):
            return candidate
    sys.exit(
        "Blender not found. Install Blender 3.6+ (free, blender.org) or pass --blender /path/to/blender "
        "or set BLENDER=/path/to/blender."
    )


def run_worker(blender, mode, payload):
    cmd = [blender, "-b", "--factory-startup", "--python", WORKER, "--", mode, json.dumps(payload)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_PREFIX):
            return json.loads(line[len(RESULT_PREFIX):])
    tail = (proc.stdout + proc.stderr)[-2000:]
    return {"ok": False, "error": f"Blender exited with {proc.returncode} and no result.\n{tail}"}


def fetch_input(path_or_url, work_dir):
    """Accept a local path or an https URL (e.g. a Sloyd glbUrl)."""
    if not path_or_url.startswith("https://"):
        if not os.path.isfile(path_or_url):
            sys.exit(f"Input not found: {path_or_url}")
        return os.path.abspath(path_or_url)
    name = os.path.basename(path_or_url.split("?")[0]) or "model.glb"
    dest = os.path.join(work_dir, name)
    with urllib.request.urlopen(path_or_url, timeout=120) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)
    return dest


def limit_problems(info, max_tris, max_tex):
    problems = []
    for mesh in info.get("meshes", []):
        if mesh["triangles"] > max_tris:
            problems.append(f"{mesh['name']}: {mesh['triangles']:,} triangles > {max_tris:,}")
        for tex in mesh.get("textures", []):
            if max(tex["size"]) > max_tex:
                problems.append(f"{mesh['name']}: texture {tex['size'][0]}x{tex['size'][1]} > {max_tex}x{max_tex}")
        if mesh.get("materials", 0) > 1:
            # Not a hard failure: the Importer splits it, but each MeshPart takes one material.
            problems.append(f"{mesh['name']}: {mesh['materials']} materials (warning: one material per MeshPart)")
    return problems


def hard_problems(problems):
    return [p for p in problems if "(warning" not in p]


def cmd_check(args):
    blender = find_blender(args.blender)
    with tempfile.TemporaryDirectory() as tmp:
        src = fetch_input(args.input, tmp)
        info = run_worker(blender, "inspect", {"input": src})
    if not info.get("ok"):
        print(json.dumps(info, indent=2))
        return 1
    hard_tex = ROBLOX_MAX_TEXTURE if args.max_texture == "auto" else int(args.max_texture)
    problems = limit_problems(info, args.max_tris, hard_tex)
    info["problems"] = problems
    info["roblox_ready"] = not hard_problems(problems)
    print(json.dumps(info, indent=2))
    return 0 if info["roblox_ready"] else 1


def process_one(blender, src, name, out_dir, opts):
    target = min(int(opts.get("target_tris") or DEFAULT_TARGET), opts["max_tris"])
    payload = {
        "input": src,
        "name": name,
        "out_dir": os.path.abspath(out_dir),
        "target_tris": target,
        "max_texture": opts["max_texture"],
        "height_studs": opts.get("height_studs"),
        "longest_studs": opts.get("longest_studs"),
        "pivot": opts.get("pivot", "bottom"),
        "formats": opts["formats"],
        "join": bool(opts.get("join")),
    }
    result = run_worker(blender, "process", payload)
    if not result.get("ok"):
        return result

    # Verify by re-importing every exported file in a clean Blender session.
    verification = {}
    for fmt, path in result["outputs"].items():
        info = run_worker(blender, "inspect", {"input": path})
        if not info.get("ok"):
            verification[fmt] = {"ok": False, "error": info.get("error")}
            continue
        problems = limit_problems(info, opts["max_tris"], result.get("texture_max", ROBLOX_MAX_TEXTURE))
        before_open = sum(m.get("open_edges", 0) for m in result["before"]["meshes"])
        after_open = sum(m.get("open_edges", 0) for m in info["meshes"])
        if after_open > before_open * 1.5 + 50:
            problems.append(
                f"open edges grew {before_open} -> {after_open} (warning: decimation may have opened holes; "
                "raise --target-tris or regenerate with a lower targetFaceCount)"
            )
        verification[fmt] = {
            "ok": not hard_problems(problems),
            "total_triangles": info["total_triangles"],
            "open_edges": after_open,
            "meshes": [{"name": m["name"], "triangles": m["triangles"], "textures": m["textures"]} for m in info["meshes"]],
            "size_studs": info["size_studs"],
            "problems": problems,
        }
    result["verification"] = verification
    result["roblox_ready"] = all(v.get("ok") for v in verification.values())
    report_path = os.path.join(out_dir, f"{name}.report.json")
    with open(report_path, "w") as fh:
        json.dump(result, fh, indent=2)
    result["report"] = report_path
    return result


def summarize(result):
    if not result.get("ok"):
        return f"FAILED {result.get('name', '')}: {result.get('error')}"
    before = result["before"]["total_triangles"]
    after = result["after"]["total_triangles"]
    size = result["after"]["size_studs"]
    status = "READY" if result["roblox_ready"] else "NOT READY"
    outs = ", ".join(os.path.basename(p) for p in result["outputs"].values())
    return (
        f"{status} {result['name']}: {before:,} -> {after:,} tris, "
        f"{size['x']}x{size['y']}x{size['z']} studs, {outs}"
    )


def common_opts(args):
    return {
        "max_tris": args.max_tris,
        "max_texture": args.max_texture,
        "target_tris": args.target_tris,
        "height_studs": args.height_studs,
        "longest_studs": args.longest_studs,
        "pivot": args.pivot,
        "formats": [f.strip() for f in args.formats.split(",") if f.strip()],
        "join": args.join,
    }


def cmd_process(args):
    blender = find_blender(args.blender)
    os.makedirs(args.out, exist_ok=True)
    src = fetch_input(args.input, args.out)
    name = args.name or os.path.splitext(os.path.basename(src))[0]
    result = process_one(blender, src, name, args.out, common_opts(args))
    print(summarize(result))
    if args.json:
        print(json.dumps(result, indent=2))
    return 0 if result.get("ok") and result.get("roblox_ready") else 1


def cmd_batch(args):
    """Process every asset in a prop-modeler manifest and write results back into it."""
    blender = find_blender(args.blender)
    with open(args.manifest) as fh:
        manifest = json.load(fh)
    base = os.path.dirname(os.path.abspath(args.manifest))
    out_root = os.path.join(base, "export")
    failures = 0
    for asset in manifest.get("assets", []):
        if args.only and asset["name"] not in args.only.split(","):
            continue
        src = asset.get("glbPath") or asset.get("glbUrl")
        if not src:
            print(f"SKIP {asset['name']}: no glbPath or glbUrl yet")
            continue
        if not src.startswith("https://") and not os.path.isabs(src):
            src = os.path.join(base, src)
        src = fetch_input(src, os.path.join(base, "raw")) if src.startswith("https://") else src
        opts = common_opts(args)
        opts["target_tris"] = asset.get("triBudget") or args.target_tris
        opts["height_studs"] = asset.get("heightStuds") or args.height_studs
        opts["longest_studs"] = asset.get("longestStuds") or args.longest_studs
        result = process_one(blender, src, asset["name"], os.path.join(out_root, asset["name"]), opts)
        print(summarize(result))
        asset["export"] = {
            "ready": bool(result.get("roblox_ready")),
            "triangles": result.get("after", {}).get("total_triangles"),
            "sizeStuds": result.get("after", {}).get("size_studs"),
            "files": {k: os.path.relpath(v, base) for k, v in result.get("outputs", {}).items()},
            "error": result.get("error"),
        }
        if not result.get("roblox_ready"):
            failures += 1
    with open(args.manifest, "w") as fh:
        json.dump(manifest, fh, indent=2)
    return 1 if failures else 0


def cmd_preview(args):
    blender = find_blender(args.blender)
    with tempfile.TemporaryDirectory() as tmp:
        src = fetch_input(args.input, tmp)
        result = run_worker(
            blender,
            "preview",
            {
                "input": src,
                "output": os.path.abspath(args.out),
                "width": args.size,
                "height": args.size,
                "samples": args.samples,
                "yaw": args.yaw,
                "transparent": not args.opaque,
            },
        )
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--blender", help="Path to the Blender executable")
    sub = p.add_subparsers(dest="cmd", required=True)

    def limits(sp):
        sp.add_argument("--max-tris", type=int, default=ROBLOX_MAX_TRIANGLES, help="Hard per-mesh limit (default 20000)")
        sp.add_argument("--max-texture", default="auto",
                        help="Max texture edge in px, or 'auto' to size by the model's stud size (default auto)")

    def shaping(sp):
        sp.add_argument("--target-tris", type=int, default=DEFAULT_TARGET, help="Decimation target per mesh (default 18000)")
        size = sp.add_mutually_exclusive_group()
        size.add_argument("--height-studs", type=float, help="Scale so the model is this tall in studs")
        size.add_argument("--longest-studs", type=float, help="Scale so the longest side is this many studs")
        sp.add_argument("--pivot", choices=["bottom", "center"], default="bottom", help="Pivot placement (default bottom)")
        sp.add_argument("--formats", default="fbx,obj,glb", help="Comma list of fbx,obj,glb (default all)")
        sp.add_argument("--join", action="store_true", help="Join all meshes into one MeshPart")

    c = sub.add_parser("check", help="Report triangles/textures and pass/fail against Roblox limits")
    c.add_argument("input")
    limits(c)
    c.set_defaults(func=cmd_check)

    pr = sub.add_parser("process", help="Decimate, rescale, re-pivot and export one model")
    pr.add_argument("input", help="GLB/FBX/OBJ path or https URL")
    pr.add_argument("--name", help="Asset name used for files and the MeshPart (PascalCase)")
    pr.add_argument("--out", default="roblox-assets/export", help="Output directory")
    pr.add_argument("--json", action="store_true", help="Also print the full JSON report")
    limits(pr)
    shaping(pr)
    pr.set_defaults(func=cmd_process)

    b = sub.add_parser("batch", help="Process every asset in a prop-modeler manifest.json")
    b.add_argument("manifest")
    b.add_argument("--only", help="Comma list of asset names to process")
    limits(b)
    shaping(b)
    b.set_defaults(func=cmd_batch)

    v = sub.add_parser("preview", help="Render a PNG still with Cycles on the CPU")
    v.add_argument("input")
    v.add_argument("--out", required=True)
    v.add_argument("--size", type=int, default=1080)
    v.add_argument("--samples", type=int, default=48)
    v.add_argument("--yaw", type=float, default=35)
    v.add_argument("--opaque", action="store_true", help="Render the world background instead of transparency")
    v.set_defaults(func=cmd_preview)
    return p


def main():
    args = build_parser().parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
