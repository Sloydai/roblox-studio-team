#!/usr/bin/env python3
"""Turn a Sloyd skybox into the six images a Roblox `Sky` object needs.

  roblox_sky.py --job sky_job.json --out roblox-assets/sky        # from get_job output (preferred)
  roblox_sky.py --faces px.png nx.png py.png ny.png pz.png nz.png --out sky
  roblox_sky.py --panorama panorama.png --out sky                 # equirectangular fallback

Writes SkyboxBk/Dn/Ft/Lf/Rt/Up.png (square, 1024 px max), preview_cross.png and sky.json.

Face order from Sloyd (`outputs.cubemapFaceUrls`): 0=+X, 1=-X, 2=+Y, 3=-Y, 4=+Z, 5=-Z.
The Roblox mapping, including the front/back swap and the up/down rotations, is the
same one Sloyd's own "Roblox cubemap" export uses (Horizon, exportFormat.service.ts, v2).

Nothing to install: it uses Pillow and NumPy when they're there, and otherwise runs itself
inside Blender (which bundles NumPy and reads PNG, JPEG and WebP). Blender is found the
same way as for prop-modeler: --blender, $BLENDER, PATH, or the default install folders.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

try:
    import bpy  # noqa: F401  (only inside Blender)

    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

try:
    import numpy as np
except ImportError:
    np = None
try:
    from PIL import Image
except ImportError:
    Image = None

ROBLOX_MAX_SKY = 1024

# (Roblox property, Sloyd face index, clockwise rotation in degrees)
ROBLOX_FACES = [
    ("SkyboxRt", 0, 0),
    ("SkyboxLf", 1, 0),
    ("SkyboxUp", 2, 90),
    ("SkyboxDn", 3, -90),
    ("SkyboxFt", 5, 0),
    ("SkyboxBk", 4, 0),
]


def _local_copy(src):
    if not src.startswith("https://"):
        return src, False
    ext = os.path.splitext(src.split("?")[0])[1] or ".png"
    fd, path = tempfile.mkstemp(suffix=ext)
    with urllib.request.urlopen(src, timeout=120) as resp, os.fdopen(fd, "wb") as out:
        out.write(resp.read())
    return path, True


def load_image(src):
    """Path or https URL -> HxWx3 uint8 array."""
    path, temp = _local_copy(src)
    try:
        if Image is not None:
            with Image.open(path) as im:
                return np.asarray(im.convert("RGB"), dtype=np.uint8).copy()
        img = bpy.data.images.load(path)
        w, h = img.size
        buf = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(buf)
        bpy.data.images.remove(img)
        arr = buf.reshape(h, w, 4)[::-1, :, :3]
        return np.clip(np.round(arr * 255), 0, 255).astype(np.uint8)
    finally:
        if temp:
            os.remove(path)


def save_image(arr, path):
    if Image is not None:
        Image.fromarray(arr).save(path)
        return
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = arr[::-1].astype(np.float32) / 255
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def resize(arr, size):
    """Square resize with area averaging for downscales and bilinear for the rest."""
    h, w = arr.shape[:2]
    if (h, w) == (size, size):
        return arr
    a = arr.astype(np.float32)
    k = min(h, w) // size
    if k >= 2:  # box-filter down by an integer factor first, so nothing aliases
        hh, ww = (h // k) * k, (w // k) * k
        a = a[:hh, :ww].reshape(hh // k, k, ww // k, k, 3).mean(axis=(1, 3))
        h, w = a.shape[:2]
    ys = (np.arange(size) + 0.5) * h / size - 0.5
    xs = (np.arange(size) + 0.5) * w / size - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, w - 1)
    y1, x1 = np.clip(y0 + 1, 0, h - 1), np.clip(x0 + 1, 0, w - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]
    fx = np.clip(xs - x0, 0, 1)[None, :, None]
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return np.clip(np.round(top * (1 - fy) + bot * fy), 0, 255).astype(np.uint8)


def rotate_clockwise(arr, degrees):
    # Matches sharp's rotate(90), which is clockwise.
    return np.rot90(arr, k=-(degrees // 90)) if degrees else arr


def faces_from_panorama(pano, size):
    """Equirectangular -> 6 faces in Sloyd's convention (exact inverse of Sloyd's stitcher)."""
    src = np.asarray(pano, dtype=np.uint8)
    h, w = src.shape[:2]
    # Pixel centers on the face, in [-1, 1]
    t = (np.arange(size) + 0.5) / size * 2 - 1
    fu, fv = np.meshgrid(t, t)  # fu along x (columns), fv along y (rows)
    one = np.ones_like(fu)
    # Direction vectors per face, inverted from cubemap-equirect.ts:
    #   +X: fu=-dz, fv=-dy   -X: fu=dz, fv=-dy   +Y: fu=dx, fv=dz
    #   -Y: fu=dx, fv=-dz    +Z: fu=dx, fv=-dy   -Z: fu=-dx, fv=-dy
    dirs = [
        (one, -fv, -fu),
        (-one, -fv, fu),
        (fu, one, fv),
        (fu, -one, -fv),
        (fu, -fv, one),
        (-fu, -fv, -one),
    ]
    faces = []
    for dx, dy, dz in dirs:
        norm = np.sqrt(dx * dx + dy * dy + dz * dz)
        dx, dy, dz = dx / norm, dy / norm, dz / norm
        lon = np.arctan2(dz, dx)  # dz = cos(lat) sin(lon), dx = cos(lat) cos(lon)
        lat = np.arcsin(np.clip(dy, -1, 1))
        x = (lon + np.pi) / (2 * np.pi) * w
        y = (np.pi / 2 - lat) / np.pi * h  # top row = north pole
        xi = np.clip(np.floor(x).astype(int), 0, w - 1)
        yi = np.clip(np.floor(y).astype(int), 0, h - 1)
        faces.append(src[yi, xi])
    return faces


def stitch_equirect(faces, out_w):
    """Python port of Sloyd's stitchEquirectangular, used to test the inverse above."""
    size = faces[0].shape[1]
    raw = [resize(f, size) for f in faces]
    out_h = out_w // 2
    xs, ys = np.meshgrid(np.arange(out_w), np.arange(out_h))
    u = xs / out_w * 2 * np.pi - np.pi
    v = -(ys / out_h * np.pi - np.pi / 2)
    dx, dy, dz = np.cos(v) * np.cos(u), np.sin(v), np.cos(v) * np.sin(u)
    ax, ay, az = np.abs(dx), np.abs(dy), np.abs(dz)
    out = np.zeros((out_h, out_w, 3), dtype=np.uint8)
    xmask = (ax >= ay) & (ax >= az)
    ymask = ~xmask & (ay >= ax) & (ay >= az)
    zmask = ~xmask & ~ymask
    with np.errstate(divide="ignore", invalid="ignore"):
        cases = [
            (xmask & (dx > 0), 0, -dz / ax, -dy / ax),
            (xmask & (dx <= 0), 1, dz / ax, -dy / ax),
            (ymask & (dy > 0), 2, dx / ay, dz / ay),
            (ymask & (dy <= 0), 3, dx / ay, -dz / ay),
            (zmask & (dz > 0), 4, dx / az, -dy / az),
            (zmask & (dz <= 0), 5, -dx / az, -dy / az),
        ]
        for mask, idx, fu, fv in cases:
            px = np.clip(np.floor((fu * 0.5 + 0.5) * size), 0, size - 1).astype(int)
            py = np.clip(np.floor((fv * 0.5 + 0.5) * size), 0, size - 1).astype(int)
            out[mask] = raw[idx][py[mask], px[mask]]
    return out


def to_roblox(faces, size):
    return {name: resize(rotate_clockwise(faces[idx], rot), size) for name, idx, rot in ROBLOX_FACES}


def preview_cross(roblox_faces, tile=256):
    """Horizontal cross: Up above Ft, Dn below; row is Lf Ft Rt Bk."""
    canvas = np.zeros((tile * 3, tile * 4, 3), dtype=np.uint8)
    canvas[:] = (11, 24, 51)
    layout = {"SkyboxUp": (1, 0), "SkyboxLf": (0, 1), "SkyboxFt": (1, 1), "SkyboxRt": (2, 1), "SkyboxBk": (3, 1), "SkyboxDn": (1, 2)}
    for name, (cx, cy) in layout.items():
        canvas[cy * tile:(cy + 1) * tile, cx * tile:(cx + 1) * tile] = resize(roblox_faces[name], tile)
    return canvas


def faces_from_job(path):
    with open(path) as fh:
        job = json.load(fh)
    job = job.get("structuredContent", job)
    outputs = job.get("outputs") or {}
    urls = outputs.get("cubemapFaceUrls") or []
    if len(urls) >= 6:
        return [load_image(u) for u in urls[:6]], job.get("jobId") or job.get("id")
    if outputs.get("panoramaUrl"):
        return None, outputs["panoramaUrl"]
    sys.exit("get_job output has neither 6 cubemapFaceUrls nor a panoramaUrl. Is the job done?")


def find_blender(explicit=None):
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, "..", "..", "prop-modeler", "scripts"))
    from roblox_mesh import find_blender as find

    return find(explicit)


def run_in_blender(argv, explicit=None):
    """No Pillow/NumPy here: rerun this script inside Blender, which has both covered."""
    blender = find_blender(explicit)
    cmd = [blender, "-b", "--factory-startup", "--python", os.path.abspath(__file__), "--"] + argv
    proc = subprocess.run(cmd, capture_output=True, text=True)
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            print(line)
    if proc.returncode != 0 or '"ok": true' not in proc.stdout:
        sys.exit("Sky conversion inside Blender failed:\n" + (proc.stdout + proc.stderr)[-1500:])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if IN_BLENDER and "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--job", help="JSON file holding the get_job result of a finished skybox job")
    src.add_argument("--faces", nargs=6, metavar="FACE", help="Six faces in Sloyd order +X -X +Y -Y +Z -Z")
    src.add_argument("--panorama", help="Equirectangular panorama (path or https URL)")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--size", type=int, default=ROBLOX_MAX_SKY, help="Face size in px (max 1024)")
    p.add_argument("--blender", help="Path to Blender, used only when Pillow/NumPy aren't installed")
    args = p.parse_args(argv)
    if not IN_BLENDER and (np is None or Image is None):
        rest = [a for a in argv]
        if args.blender:
            i = rest.index("--blender")
            del rest[i:i + 2]
        for flag in ("--job", "--panorama", "--out"):
            if flag in rest:
                i = rest.index(flag) + 1
                if not rest[i].startswith("https://"):
                    rest[i] = os.path.abspath(rest[i])
        if "--faces" in rest:
            i = rest.index("--faces") + 1
            rest[i:i + 6] = [x if x.startswith("https://") else os.path.abspath(x) for x in rest[i:i + 6]]
        return run_in_blender(rest, args.blender)

    size = min(args.size, ROBLOX_MAX_SKY)
    source = None
    if args.job:
        faces, ref = faces_from_job(args.job)
        if faces is None:
            faces = faces_from_panorama(load_image(ref), size)
            source = "panorama"
        else:
            source = "cubemapFaceUrls"
    elif args.faces:
        faces, source = [load_image(f) for f in args.faces], "faces"
    else:
        faces, source = faces_from_panorama(load_image(args.panorama), size), "panorama"

    os.makedirs(args.out, exist_ok=True)
    roblox = to_roblox(faces, size)
    for name, img in roblox.items():
        save_image(img, os.path.join(args.out, f"{name}.png"))
    save_image(preview_cross(roblox), os.path.join(args.out, "preview_cross.png"))
    manifest = {
        "source": source,
        "faceSize": size,
        "files": {name: f"{name}.png" for name in roblox},
        # Fill in after uploading each PNG as a Decal/Image in Studio (Asset Manager -> Bulk Import).
        "assetIds": {name: None for name in roblox},
    }
    with open(os.path.join(args.out, "sky.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    backend = "blender" if Image is None else "pillow"
    print(json.dumps({"ok": True, "out": args.out, "source": source, "faceSize": size, "backend": backend}))


if __name__ == "__main__":
    main()
