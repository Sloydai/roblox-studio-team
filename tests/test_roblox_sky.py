"""Tests for roblox_sky.py. Needs Pillow and NumPy (tests/requirements.txt); the no-Pillow test needs Blender.

  python3 -m unittest discover -s tests -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "world-backdrop", "scripts")
sys.path.insert(0, SCRIPTS)
SKY = os.path.join(SCRIPTS, "roblox_sky.py")


def run(cmd):
    return subprocess.run([sys.executable] + cmd, capture_output=True, text=True)


class SkyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def synthetic_panorama(self, w=1024):
        import numpy as np

        h = w // 2
        xs, ys = np.meshgrid(np.arange(w), np.arange(h))
        lon = xs / w * 2 * np.pi - np.pi
        lat = np.pi / 2 - ys / h * np.pi
        # Colour = direction vector, so any orientation error changes pixel values.
        dx, dy, dz = np.cos(lat) * np.cos(lon), np.sin(lat), np.cos(lat) * np.sin(lon)
        return np.stack([(dx + 1) * 127.5, (dy + 1) * 127.5, (dz + 1) * 127.5], axis=-1).astype("uint8")

    def test_panorama_round_trip_matches_sloyd_stitcher(self):
        import numpy as np
        import roblox_sky

        pano = self.synthetic_panorama()
        faces = roblox_sky.faces_from_panorama(pano, 256)
        back = roblox_sky.stitch_equirect(faces, pano.shape[1])
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
        from PIL import Image

        Image.fromarray(self.synthetic_panorama(2048)).save(pano)
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


    @unittest.skipUnless(os.environ.get("BLENDER") or shutil.which("blender"), "Blender not found")
    def test_without_pillow_runs_in_blender_and_matches(self):
        from PIL import Image
        import numpy as np

        pano = os.path.join(self.tmp, "pano.png")
        Image.fromarray(self.synthetic_panorama(1024)).save(pano)
        a, b = os.path.join(self.tmp, "a"), os.path.join(self.tmp, "b")
        self.assertEqual(run([SKY, "--panorama", pano, "--out", a, "--size", "256"]).returncode, 0)
        # Hide Pillow from the script to force the Blender path.
        block = os.path.join(self.tmp, "block")
        os.makedirs(os.path.join(block, "PIL"))
        with open(os.path.join(block, "PIL", "__init__.py"), "w") as fh:
            fh.write("raise ImportError('blocked for test')\n")
        env = dict(os.environ, PYTHONPATH=block)
        proc = subprocess.run([sys.executable, SKY, "--panorama", pano, "--out", b, "--size", "256"],
                              capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"backend": "blender"', proc.stdout)
        for name in ("SkyboxBk", "SkyboxDn", "SkyboxFt", "SkyboxLf", "SkyboxRt", "SkyboxUp"):
            x = np.asarray(Image.open(os.path.join(a, name + ".png")).convert("RGB"), dtype=float)
            y = np.asarray(Image.open(os.path.join(b, name + ".png")).convert("RGB"), dtype=float)
            self.assertEqual(x.shape, y.shape)
            self.assertLess(np.abs(x - y).mean(), 1.0, name)


if __name__ == "__main__":
    unittest.main()
