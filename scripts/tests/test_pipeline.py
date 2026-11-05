"""Tests for roblox_mesh.py and roblox_sky.py.

  python -m unittest discover -s scripts/tests -v

Mesh tests need Blender (set BLENDER or put `blender` on PATH); they are skipped without it.
The real-model test downloads a CC BY 4.0 model from Sloyd's free asset library
("Pinker Cupcake In Roblox Style", job lp2sbs70); set ROBLOX_TEST_OFFLINE=1 to skip it.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

MESH = os.path.join(SCRIPTS, "roblox_mesh.py")
SKY = os.path.join(SCRIPTS, "roblox_sky.py")
REAL_MODEL_URL = "https://storage.googleapis.com/ai-services-quality/jobs/lp2sbs70.glb"


def blender_path():
    for c in (os.environ.get("BLENDER"), shutil.which("blender")):
        if c and os.path.isfile(c):
            return c
    return None


BLENDER = blender_path()

# Builds a 2048px-textured, ~80k-triangle UV sphere: over both Roblox limits.
MAKE_HEAVY_GLB = r"""
import bpy, sys
out = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=256, radius=1.5, ring_count=160)
obj = bpy.context.active_object
img = bpy.data.images.new("Checker", 2048, 2048)
img.generated_type = "COLOR_GRID"
img.pack()
mat = bpy.data.materials.new("Mat")
mat.use_nodes = True
tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = img
mat.node_tree.links.new(tex.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
obj.data.materials.append(mat)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB")
"""


def run(cmd):
    return subprocess.run([sys.executable] + cmd, capture_output=True, text=True)


@unittest.skipUnless(BLENDER, "Blender not found (set BLENDER)")
class MeshPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.heavy = os.path.join(cls.tmp, "heavy.glb")
        script = os.path.join(cls.tmp, "make.py")
        with open(script, "w") as fh:
            fh.write(MAKE_HEAVY_GLB)
        subprocess.run([BLENDER, "-b", "--factory-startup", "--python", script, "--", cls.heavy], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_check_flags_over_limit_model(self):
        proc = run([MESH, "check", self.heavy, "--max-texture", "1024"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        info = json.loads(proc.stdout)
        self.assertGreater(info["total_triangles"], 20000)
        self.assertFalse(info["roblox_ready"])
        self.assertTrue(any("triangles" in p for p in info["problems"]))
        self.assertTrue(any("texture" in p for p in info["problems"]))

    def test_process_fits_limits_and_exports_all_formats(self):
        out = os.path.join(self.tmp, "out")
        proc = run([MESH, "process", self.heavy, "--name", "Gumball", "--height-studs", "6", "--out", out, "--json"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.load(open(os.path.join(out, "Gumball.report.json")))
        self.assertTrue(report["roblox_ready"])
        for fmt in ("fbx", "obj", "glb"):
            path = os.path.join(out, f"Gumball.{fmt}")
            self.assertTrue(os.path.isfile(path), path)
            v = report["verification"][fmt]
            self.assertTrue(v["ok"], v)
            self.assertLessEqual(v["total_triangles"], 18000)
            self.assertGreater(v["total_triangles"], 12000, "decimated far more than asked")
            self.assertAlmostEqual(v["size_studs"]["y"], 6.0, places=2)
            # The sphere is exported flat-shaded (a triangle soup); welding must keep it closed.
            self.assertLess(v["open_edges"], 50, "decimation opened holes")
            self.assertFalse([p for p in v["problems"] if "open edges" in p])
            # 6-stud model -> Roblox guidance says 512 px.
            self.assertEqual(report["texture_max"], 512)
            for mesh in v["meshes"]:
                for tex in mesh["textures"]:
                    self.assertLessEqual(max(tex["size"]), 512)
        self.assertTrue(os.path.isfile(os.path.join(out, "textures", "Gumball_0.png")))
        with open(os.path.join(out, "Gumball.mtl")) as fh:
            self.assertIn("map_Kd textures/Gumball_0.png", fh.read())

    def test_custom_budget_and_center_pivot(self):
        out = os.path.join(self.tmp, "budget")
        proc = run([MESH, "process", self.heavy, "--name", "Coin", "--target-tris", "2000", "--pivot", "center",
                    "--formats", "obj", "--out", out])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.load(open(os.path.join(out, "Coin.report.json")))
        self.assertLessEqual(report["verification"]["obj"]["total_triangles"], 2000)
        self.assertEqual(list(report["outputs"]), ["obj"])

    def test_batch_updates_manifest(self):
        base = os.path.join(self.tmp, "batch")
        os.makedirs(os.path.join(base, "raw"))
        shutil.copy(self.heavy, os.path.join(base, "raw", "heavy.glb"))
        manifest = {"assets": [{"name": "GumdropPlatform", "glbPath": "raw/heavy.glb", "triBudget": 4000, "heightStuds": 2}]}
        path = os.path.join(base, "manifest.json")
        json.dump(manifest, open(path, "w"))
        proc = run([MESH, "batch", path, "--formats", "fbx"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        exported = json.load(open(path))["assets"][0]["export"]
        self.assertTrue(exported["ready"])
        self.assertLessEqual(exported["triangles"], 4000)
        self.assertTrue(os.path.isfile(os.path.join(base, exported["files"]["fbx"])))

    @unittest.skipIf(os.environ.get("ROBLOX_TEST_OFFLINE"), "offline")
    def test_real_sloyd_model(self):
        src = os.path.join(self.tmp, "cupcake.glb")
        urllib.request.urlretrieve(REAL_MODEL_URL, src)
        out = os.path.join(self.tmp, "cupcake")
        proc = run([MESH, "process", src, "--name", "PinkCupcake", "--height-studs", "4", "--out", out])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.load(open(os.path.join(out, "PinkCupcake.report.json")))
        self.assertGreater(report["before"]["total_triangles"], 20000)
        self.assertTrue(report["roblox_ready"])
        self.assertLessEqual(report["verification"]["fbx"]["total_triangles"], 18000)
        self.assertEqual(report["texture_max"], 256)  # 4-stud model


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
