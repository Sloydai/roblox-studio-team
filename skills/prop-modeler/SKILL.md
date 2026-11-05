---
name: prop-modeler
description: Use when a Roblox game needs 3D props or cosmetics from Sloyd, or when an existing GLB/FBX/OBJ must become Roblox-ready. Examples are "generate the props for my obby", "this mesh is over the Roblox triangle limit", "decimate for Roblox" or "export FBX for MeshPart import". Generates in one consistent style, then checks and decimates to the 20,000-triangle MeshPart limit, scales to studs, sets a ground pivot, sizes textures and exports verified FBX/OBJ/GLB.
---

# Prop Modeler

You produce Roblox-ready meshes. Generation is Sloyd's job; making them pass Roblox's limits is yours, and you verify every file.

Load the sloyd-api skill first (credentials, credits, job loop, errors), and read `${CLAUDE_PLUGIN_ROOT}/skills/studio-importer/references/roblox-reference.md`.

## Inputs

`roblox-assets/plan.json` from game-designer. For a single ad-hoc prop, build a one-asset plan in your head with the same fields (name, role, prompt, heightStuds, triBudget).

## 1. Cost check

Call `get_credit_balance`. Cost = 25 credits per textured text-to-3D model. Show the total and wait for a yes, unless roblox-producer already got one for this plan.

## 2. Generate (max 5 jobs in flight)

For each asset call `generate_3d_from_text` with:

```json
{
  "prompt": "<asset.prompt>, <style.promptSuffix>",
  "genStyleId": "<style.genStyleId>",
  "topology": "triangles",
  "targetFaceCount": <asset.triBudget>,
  "textureResolution": "1k"
}
```

- Asking for the budget up front means most models arrive already under the limit. The local exporter is the safety net.
- If the plan has a concept image for the asset, use `generate_3d_from_image` with `imageJobId` instead (20 credits).
- Write each `jobId` into `roblox-assets/manifest.json` as soon as it comes back (shape below). Submit 5, then poll with `get_job` (`wait: 30`) and submit the next as each finishes. On 429, wait for a running job. On 402, stop and report.
- On `success`, download: `curl -fsSL -o roblox-assets/raw/<Name>.glb "<outputs.glbUrl>"`.
- On `error`, retry once with a simpler prompt (one object, fewer adjectives). Credits for failed jobs are refunded.

`manifest.json`:

```json
{ "game": "...", "style": { ... }, "assets": [
  { "name": "GumdropPlatform", "role": "platform", "heightStuds": 3, "triBudget": 3000, "collision": "PreciseConvexDecomposition",
    "prompt": "...", "jobId": "01J...", "status": "success", "glbUrl": "https://...", "glbPath": "raw/GumdropPlatform.glb" }
] }
```

## 3. Make them Roblox-ready

Requires Blender 3.6+ (free). The script finds it on PATH, at the default install location, or via `BLENDER=/path/to/blender`.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prop-modeler/scripts/roblox_mesh.py batch roblox-assets/manifest.json
```

For each asset this:
1. Imports the GLB and welds split vertices, so decimation can't open holes along UV seams.
2. Collapse-decimates any mesh above `triBudget`, never above 18,000 (the hard limit is 20,000 per mesh).
3. Scales to `heightStuds` (1 unit = 1 stud; leave the Importer's Scale Unit on **Stud**).
4. Moves the pivot to bottom-center, so the model sits on the ground when placed.
5. Downscales textures to Roblox's guidance for its size: 256 px for about 5 studs, 512 for 10, 1024 for 20.
6. Exports `export/<Name>/<Name>.fbx` (embedded textures, Z forward / Y up / FBX Unit Scale, per Roblox's Blender guide), `.obj` + `.mtl` + `textures/`, and `.glb`.
7. Re-imports every exported file in a clean Blender session and checks triangles, textures, size and open edges. Results go to `<Name>.report.json` and the asset's `export` block in the manifest.

Single file: `roblox_mesh.py process <glb|url> --name <Name> --height-studs 4 --target-tris 3000`.
Audit any file: `roblox_mesh.py check model.fbx` (exit 1 if over the limits).

## 4. Review

Render previews and look at them before handing off:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prop-modeler/scripts/roblox_mesh.py preview roblox-assets/export/<Name>/<Name>.glb --out roblox-assets/previews/<Name>.png
```

Reject and regenerate if the silhouette is wrong, a platform top isn't flat enough to stand on, or there are visible holes. If the report shows "open edges grew", raise `triBudget` for that asset.

## Hand-off

Report a table: name, role, triangles before → after, size in studs, `ready`. Every asset must be `ready: true`. Base `jobId`s stay in the manifest, because skin-variants needs them.

Notes:
- `split_model_into_parts` (40 credits) is for when you want separately animated or coloured pieces, such as a door or a lid. Parts come back as separate meshes, so each becomes its own MeshPart.
- Roblox avatar bodies and selfie-to-avatar aren't in Sloyd's public API yet ("coming soon"). This skill makes props and back-worn cosmetics, not avatar bodies or layered clothing.
