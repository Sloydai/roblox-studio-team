"""Blender-side worker for roblox_mesh.py. Run it through roblox_mesh.py, not directly.

    blender -b --factory-startup --python blender_roblox.py -- <mode> <json-args>

Modes:
  process  import a model, fit it to Roblox limits, export FBX/OBJ/GLB
  inspect  import a model and report triangles, meshes, materials and textures
  preview  render a PNG still of a model (Cycles on the CPU, no GPU needed)

Writes one JSON line prefixed with ROBLOX_RESULT= to stdout.
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

RESULT_PREFIX = "ROBLOX_RESULT="


def emit(payload):
    sys.stdout.write(RESULT_PREFIX + json.dumps(payload) + "\n")
    sys.stdout.flush()


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    # Roblox's Blender guide: unit system None so 1 Blender unit = 1 stud.
    scene.unit_settings.system = "NONE"
    scene.unit_settings.scale_length = 1.0


def import_model(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        # merge_vertices welds the UV-seam splits glTF stores, so decimation
        # does not open cracks along seams. UVs stay per face corner.
        bpy.ops.import_scene.gltf(filepath=path, merge_vertices=True)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    else:
        raise ValueError(f"Unsupported input format: {ext}")


def mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def triangle_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def open_edge_count(obj):
    """Boundary edges after welding by position. 0 = watertight (Roblox asks for watertight)."""
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    count = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    return count


def material_images(mat):
    images = []
    if mat and mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image is not None:
                images.append(node.image)
    return images


def describe(objs):
    meshes = []
    for o in objs:
        mats = [s.material for s in o.material_slots if s.material]
        textures = []
        for m in mats:
            for img in material_images(m):
                textures.append({"name": img.name, "size": list(img.size)})
        meshes.append(
            {
                "name": o.name,
                "open_edges": open_edge_count(o),
                "triangles": triangle_count(o),
                "vertices": len(o.data.vertices),
                "materials": len(mats),
                "textures": textures,
            }
        )
    lo, hi = world_bounds(objs)
    size = [hi[i] - lo[i] for i in range(3)] if objs else [0, 0, 0]
    return {
        "meshes": meshes,
        "total_triangles": sum(m["triangles"] for m in meshes),
        # Blender is Z-up; report Roblox order (X, Y=up, Z).
        "size_studs": {"x": round(size[0], 3), "y": round(size[2], 3), "z": round(size[1], 3)},
    }


def world_bounds(objs):
    """Bounds from the actual vertices; o.bound_box can be stale right after import."""
    import numpy as np

    bpy.context.view_layer.update()
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for o in objs:
        n = len(o.data.vertices)
        if n == 0:
            continue
        co = np.empty(n * 3)
        o.data.vertices.foreach_get("co", co)
        co = co.reshape(n, 3)
        m = np.array(o.matrix_world)
        world = co @ m[:3, :3].T + m[:3, 3]
        lo = np.minimum(lo, world.min(axis=0))
        hi = np.maximum(hi, world.max(axis=0))
    if not np.isfinite(lo).all():
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return Vector(lo.tolist()), Vector(hi.tolist())


def flatten_hierarchy(objs):
    """Bake parent transforms into the meshes and drop helper empties."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)


def join_meshes(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return mesh_objects()


def apply_modifier(obj, mod):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def triangulate(obj):
    mod = obj.modifiers.new("Triangulate", "TRIANGULATE")
    apply_modifier(obj, mod)


def weld(obj):
    """Merge coincident vertices so flat-shaded or split meshes decimate as one surface.

    Without this, a mesh exported as a triangle soup loses whole faces (holes) when
    decimated. UVs live on face corners in Blender, so welding keeps UV seams.
    """
    import bmesh

    lo, hi = world_bounds([obj])
    dist = max((hi - lo).length * 1e-6, 1e-7)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    before = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    after = len(bm.verts)
    bm.to_mesh(obj.data)
    bm.free()
    return before - after


def shade_by_angle(obj, degrees=30.0):
    """Drop stale custom normals and smooth by angle, keeping hard edges on low-poly shapes."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    if hasattr(bpy.ops.object, "shade_smooth_by_angle"):  # Blender 4.1+
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(degrees))
    else:  # Blender 3.6 / 4.0
        bpy.ops.object.shade_smooth()
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(degrees)


def decimate_to(obj, target):
    """Collapse-decimate until the mesh is at or under `target` triangles."""
    passes = 0
    while triangle_count(obj) > target and passes < 4:
        current = triangle_count(obj)
        # Aim 2% under so a single pass usually lands below the target.
        ratio = max(0.001, (target * 0.98) / current)
        mod = obj.modifiers.new("Decimate", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        apply_modifier(obj, mod)
        passes += 1
    return passes


def texture_size_for(objs):
    """Roblox texture guidance: ~5-stud objects 256, ~10 512, ~20 1024, bigger 2048."""
    lo, hi = world_bounds(objs)
    longest = max(hi - lo)
    for limit, size in ((5.5, 256), (11, 512), (22, 1024)):
        if longest <= limit:
            return size
    return 2048


def downscale_textures(max_size):
    changed = []
    for img in bpy.data.images:
        w, h = img.size
        if w == 0 or h == 0:
            continue
        longest = max(w, h)
        if longest <= max_size:
            continue
        scale = max_size / longest
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        img.scale(nw, nh)
        changed.append({"name": img.name, "from": [w, h], "to": [nw, nh]})
    return changed


def save_textures(tex_dir, base):
    """Write every texture to disk as PNG so OBJ/MTL can reference real files."""
    os.makedirs(tex_dir, exist_ok=True)
    written = []
    for i, img in enumerate(bpy.data.images):
        if img.size[0] == 0:
            continue
        path = os.path.join(tex_dir, f"{base}_{i}.png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        if img.packed_file:
            img.unpack(method="REMOVE")
        img.filepath = path
        img.reload()
        written.append(path)
    return written


def fit_scale(objs, height_studs, longest_studs):
    lo, hi = world_bounds(objs)
    size = hi - lo
    if height_studs:
        current = size.z  # Blender Z = Roblox Y (up)
        target = height_studs
    elif longest_studs:
        current = max(size)
        target = longest_studs
    else:
        return 1.0
    if current <= 0:
        return 1.0
    factor = target / current
    for o in objs:
        o.scale = o.scale * factor
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return factor


def set_pivot(objs, mode):
    """Move geometry so the pivot is bottom-center (sits on the ground) or center."""
    lo, hi = world_bounds(objs)
    center = (lo + hi) / 2
    offset = Vector((center.x, center.y, lo.z if mode == "bottom" else center.z))
    for o in objs:
        o.location -= offset
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


def export_all(out_dir, name, formats):
    paths = {}
    bpy.ops.object.select_all(action="SELECT")
    if "fbx" in formats:
        p = os.path.join(out_dir, f"{name}.fbx")
        # Roblox's Blender export guide: FBX Unit Scale, Z forward, Y up.
        bpy.ops.export_scene.fbx(
            filepath=p,
            use_selection=True,
            apply_scale_options="FBX_SCALE_UNITS",
            axis_forward="Z",
            axis_up="Y",
            mesh_smooth_type="FACE",
            path_mode="COPY",
            embed_textures=True,
            add_leaf_bones=False,
            bake_anim=False,
        )
        paths["fbx"] = p
    if "obj" in formats:
        p = os.path.join(out_dir, f"{name}.obj")
        bpy.ops.wm.obj_export(
            filepath=p,
            export_selected_objects=True,
            forward_axis="NEGATIVE_Z",
            up_axis="Y",
            export_materials=True,
            path_mode="RELATIVE",
            export_triangulated_mesh=True,
        )
        paths["obj"] = p
    if "glb" in formats:
        p = os.path.join(out_dir, f"{name}.glb")
        bpy.ops.export_scene.gltf(
            filepath=p,
            export_format="GLB",
            use_selection=True,
            export_yup=True,
            export_apply=True,
        )
        paths["glb"] = p
    return paths


def mode_inspect(args):
    reset_scene()
    import_model(args["input"])
    objs = mesh_objects()
    emit({"ok": True, "input": args["input"], **describe(objs)})


def mode_process(args):
    reset_scene()
    import_model(args["input"])
    objs = mesh_objects()
    if not objs:
        raise RuntimeError("No mesh found in input")
    before = describe(objs)

    flatten_hierarchy(objs)
    objs = mesh_objects()
    if args.get("join") and len(objs) > 1:
        objs = join_meshes(objs)

    for o in objs:
        triangulate(o)

    target = int(args["target_tris"])
    decimated = []
    for o in objs:
        start = triangle_count(o)
        if start > target:
            welded = weld(o)
            passes = decimate_to(o, target)
            shade_by_angle(o)
            decimated.append(
                {"mesh": o.name, "from": start, "to": triangle_count(o), "passes": passes, "welded_vertices": welded}
            )

    scale = fit_scale(objs, args.get("height_studs"), args.get("longest_studs"))
    set_pivot(objs, args.get("pivot", "bottom"))
    max_texture = args["max_texture"]
    if max_texture == "auto":
        max_texture = texture_size_for(objs)
    textures = downscale_textures(int(max_texture))

    out_dir = args["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    name = args["name"]
    saved = save_textures(os.path.join(out_dir, "textures"), name)
    paths = export_all(out_dir, name, args["formats"])
    after = describe(mesh_objects())

    emit(
        {
            "ok": True,
            "name": name,
            "input": args["input"],
            "before": before,
            "after": after,
            "decimated": decimated,
            "scale_factor": round(scale, 6),
            "texture_max": int(max_texture),
            "textures_downscaled": textures,
            "textures_written": saved,
            "outputs": paths,
        }
    )


def mode_preview(args):
    reset_scene()
    import_model(args["input"])
    objs = mesh_objects()
    lo, hi = world_bounds(objs)
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(args.get("samples", 48))
    scene.cycles.use_denoising = True
    scene.render.resolution_x = int(args.get("width", 1080))
    scene.render.resolution_y = int(args.get("height", 1080))
    scene.render.film_transparent = bool(args.get("transparent", True))
    scene.view_settings.view_transform = "Standard"

    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    yaw = math.radians(float(args.get("yaw", 35)))
    pitch = math.radians(float(args.get("pitch", 20)))
    dist = radius / math.tan(math.radians(18)) * 1.15
    cam.location = center + Vector(
        (math.sin(yaw) * math.cos(pitch) * dist, -math.cos(yaw) * math.cos(pitch) * dist, math.sin(pitch) * dist)
    )
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    for loc, energy in (((1, -1, 1.5), 4.0), ((-1.2, -0.4, 0.8), 1.5), ((0, 1.2, 1.2), 2.5)):
        light_data = bpy.data.lights.new("Light", "SUN")
        light_data.energy = energy
        light = bpy.data.objects.new("Light", light_data)
        scene.collection.objects.link(light)
        light.rotation_euler = (-Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    scene.render.filepath = args["output"]
    bpy.ops.render.render(write_still=True)
    emit({"ok": True, "output": args["output"]})


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) != 2:
        emit({"ok": False, "error": "usage: -- <mode> <json-args>"})
        sys.exit(2)
    mode, raw = argv
    args = json.loads(raw)
    try:
        {"inspect": mode_inspect, "process": mode_process, "preview": mode_preview}[mode](args)
    except Exception as exc:  # report to the launcher instead of a bare traceback
        emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        sys.exit(1)


main()
