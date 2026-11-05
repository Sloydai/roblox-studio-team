#!/usr/bin/env python3
"""Turn a Sloyd skybox into the six images a Roblox `Sky` object needs.

  roblox_sky.py --job get_job.json --out roblox-assets/sky        # from get_job output (preferred)
  roblox_sky.py --faces px.png nx.png py.png ny.png pz.png nz.png --out sky
  roblox_sky.py --panorama panorama.png --out sky                 # equirectangular fallback

Writes SkyboxBk/Dn/Ft/Lf/Rt/Up.png (square, 1024 px max), preview_cross.png and sky.json.

Face order from Sloyd (`outputs.cubemapFaceUrls`): 0=+X, 1=-X, 2=+Y, 3=-Y, 4=+Z, 5=-Z.
The Roblox mapping, including the front/back swap and the up/down rotations, is the
same one Sloyd's own "Roblox cubemap" export uses (Horizon, exportFormat.service.ts, v2).

Requires: pillow, numpy (see requirements.txt).
"""

import argparse
import io
import json
import os
import sys
import urllib.request

import numpy as np
from PIL import Image

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


def load_image(src):
    if src.startswith("https://"):
        with urllib.request.urlopen(src, timeout=120) as resp:
            return Image.open(io.BytesIO(resp.read())).convert("RGB")
    return Image.open(src).convert("RGB")


def rotate_clockwise(img, degrees):
    # PIL rotates counter-clockwise; sharp's rotate(90) (used by Sloyd) is clockwise.
    return img.rotate(-degrees, expand=True) if degrees else img


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
        faces.append(Image.fromarray(src[yi, xi]))
    return faces


def stitch_equirect(faces, out_w):
    """Python port of Sloyd's stitchEquirectangular, used to test the inverse above."""
    size = faces[0].size[0]
    raw = [np.asarray(f.resize((size, size)), dtype=np.uint8) for f in faces]
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
    return Image.fromarray(out)


def to_roblox(faces, size):
    result = {}
    for name, idx, rot in ROBLOX_FACES:
        img = rotate_clockwise(faces[idx], rot)
        if img.size != (size, size):
            img = img.resize((size, size), Image.LANCZOS)
        result[name] = img
    return result


def preview_cross(roblox_faces, tile=256):
    """Horizontal cross: Up above Ft, Dn below; row is Lf Ft Rt Bk."""
    canvas = Image.new("RGB", (tile * 4, tile * 3), (11, 24, 51))
    layout = {"SkyboxUp": (1, 0), "SkyboxLf": (0, 1), "SkyboxFt": (1, 1), "SkyboxRt": (2, 1), "SkyboxBk": (3, 1), "SkyboxDn": (1, 2)}
    for name, (cx, cy) in layout.items():
        canvas.paste(roblox_faces[name].resize((tile, tile), Image.LANCZOS), (cx * tile, cy * tile))
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


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--job", help="JSON file holding the get_job result of a finished skybox job")
    src.add_argument("--faces", nargs=6, metavar="FACE", help="Six faces in Sloyd order +X -X +Y -Y +Z -Z")
    src.add_argument("--panorama", help="Equirectangular panorama (path or https URL)")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--size", type=int, default=ROBLOX_MAX_SKY, help="Face size in px (max 1024)")
    args = p.parse_args()

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
        img.save(os.path.join(args.out, f"{name}.png"))
    preview_cross(roblox).save(os.path.join(args.out, "preview_cross.png"))
    manifest = {
        "source": source,
        "faceSize": size,
        "files": {name: f"{name}.png" for name in roblox},
        # Fill in after uploading each PNG as a Decal/Image in Studio (Asset Manager -> Bulk Import).
        "assetIds": {name: None for name in roblox},
    }
    with open(os.path.join(args.out, "sky.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(json.dumps({"ok": True, "out": args.out, "source": source, "faceSize": size}))


if __name__ == "__main__":
    main()
