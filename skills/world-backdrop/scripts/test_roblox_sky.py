"""Tests for roblox_sky.py. Needs Pillow and NumPy (requirements.txt), no Blender.

  python3 -m unittest discover -s skills/world-backdrop/scripts -p "test_*.py" -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SKY = os.path.join(HERE, "roblox_sky.py")


def run(cmd):
    return subprocess.run([sys.executable] + cmd, capture_output=True, text=True)


class SkyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def synthetic_panorama(self, w=1024):
        import numpy as np
        from PIL import Image

        h = w // 2
        xs, ys = np.meshgrid(np.arange(w), np.arange(h))
        lon = xs / w * 2 * np.pi - np.pi
        lat = np.pi / 2 - ys / h * np.pi
        # Colour = direction vector, so any orientation error changes pixel values.
        dx, dy, dz = np.cos(lat) * np.cos(lon), np.sin(lat), np.cos(lat) * np.sin(lon)
        rgb = np.stack([(dx + 1) * 127.5, (dy + 1) * 127.5, (dz + 1) * 127.5], axis=-1).astype("uint8")
        return Image.fromarray(rgb)

    def test_panorama_round_trip_matches_sloyd_stitcher(self):
        import numpy as np
        import roblox_sky

        pano = self.synthetic_panorama()
        faces = roblox_sky.faces_from_panorama(pano, 256)
        back = roblox_sky.stitch_equirect(faces, pano.size[0])
        err = np.abs(np.asarray(back, dtype=float) - np.asarray(pano, dtype=float)).mean()
        self.assertLess(err, 2.0, f"mean abs error {err:.2f}")

    def test_face_directions(self):
        import numpy as np
        import roblox_sky

        faces = roblox_sky.faces_from_panorama(self.synthetic_panorama(), 64)
        expected = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        for face, axis in zip(faces, expected):
            centre = np.asarray(face, dtype=float)[32, 32] / 127.5 - 1
            np.testing.assert_allclose(centre, axis, atol=0.06)

    def test_cli_writes_six_roblox_faces(self):
        pano = os.path.join(self.tmp, "pano.png")
        self.synthetic_panorama(2048).save(pano)
        out = os.path.join(self.tmp, "sky")
        proc = run([SKY, "--panorama", pano, "--out", out, "--size", "2048"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        from PIL import Image

        for name in ("SkyboxBk", "SkyboxDn", "SkyboxFt", "SkyboxLf", "SkyboxRt", "SkyboxUp"):
            img = Image.open(os.path.join(out, f"{name}.png"))
            self.assertEqual(img.size, (1024, 1024), "faces must be capped at 1024")
        manifest = json.load(open(os.path.join(out, "sky.json")))
        self.assertEqual(len(manifest["files"]), 6)
        self.assertTrue(os.path.isfile(os.path.join(out, "preview_cross.png")))

    def test_roblox_mapping_matches_sloyd_export(self):
        import roblox_sky

        mapping = {name: (idx, rot) for name, idx, rot in roblox_sky.ROBLOX_FACES}
        self.assertEqual(mapping["SkyboxFt"], (5, 0))
        self.assertEqual(mapping["SkyboxBk"], (4, 0))
        self.assertEqual(mapping["SkyboxUp"], (2, 90))
        self.assertEqual(mapping["SkyboxDn"], (3, -90))


if __name__ == "__main__":
    unittest.main()
