---
name: world-backdrop
description: Generates a 360° skybox with Sloyd (generate_skybox, generate_skybox_from_image, edit_skybox) and converts it into the six cubemap faces of a Roblox Sky object (SkyboxBk/Dn/Ft/Lf/Rt/Up) with the right orientation, plus matching Lighting settings. Use for any custom Roblox sky or environment backdrop.
when_to_use: 'Trigger phrases: custom skybox for Roblox, make a sky for my game, Roblox Sky cubemap, change the sky, sunset sky.'
argument-hint: '[sky description]'
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/roblox_sky.py *)
---

# World Backdrop

The sky is the cheapest way to make a Roblox game look like its own place: one job, six images, no triangles.

Read `${CLAUDE_PLUGIN_ROOT}/docs/sloyd-api.md`.

## 1. Prompt

Use `plan.json → skybox`, or write one: a horizon, a sky gradient, distant shapes only. Nothing close to the camera, because a sky is infinitely far away and near objects look flat. Match the game's palette and `genStyleId`.

Good: "pastel candy land sky at golden hour, cotton candy clouds, distant lollipop hills on the horizon".
Avoid: characters, text, ground details under the player.

## 2. Generate (25 credits)

`get_credit_balance` first, then `generate_skybox { "prompt": ..., "genStyleId": ... }`. If the user has reference art, upload it with `upload_image` and use `generate_skybox_from_image { "imageJobId": ... }`. For a tweak ("make it night"), use `edit_skybox { "jobId": ..., "prompt": ... }`.

Poll `get_job` (`wait: 30`) until done. Save the full `get_job` result to `roblox-assets/sky/sky_job.json`.

## 3. Convert to Roblox faces

```bash
python3 -m venv "${CLAUDE_PLUGIN_DATA}/venv" && "${CLAUDE_PLUGIN_DATA}/venv/bin/pip" install -q -r ${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt
"${CLAUDE_PLUGIN_DATA}/venv/bin/python" ${CLAUDE_PLUGIN_ROOT}/scripts/roblox_sky.py --job roblox-assets/sky/sky_job.json --out roblox-assets/sky
```

(Skip the venv lines if Pillow and NumPy are already installed.)

- Uses `outputs.cubemapFaceUrls` (order +X, −X, +Y, −Y, +Z, −Z) with the same mapping as Sloyd's own Roblox cubemap export: front and back swapped, Up rotated 90° clockwise, Down 90° counter-clockwise.
- Falls back to `outputs.panoramaUrl` (equirectangular) if faces are missing. That conversion is tested as an exact inverse of Sloyd's stitcher.
- Writes `SkyboxBk/Dn/Ft/Lf/Rt/Up.png` (1024 px), `preview_cross.png` to check seams, and `sky.json` with empty `assetIds`.

Open `preview_cross.png` and check that the horizon lines up across Lf, Ft, Rt and Bk.

## 4. Into Roblox

1. Studio → **Asset Manager** → **Bulk Import** the six PNGs (or File → Import). Each upload gets an image asset id.
2. Put the ids in `roblox-assets/sky/sky.json` and in `GameConfig.Sky`:
   ```lua
   Config.Sky = { SkyboxBk = "rbxassetid://...", SkyboxDn = "rbxassetid://...", SkyboxFt = "rbxassetid://...",
                  SkyboxLf = "rbxassetid://...", SkyboxRt = "rbxassetid://...", SkyboxUp = "rbxassetid://..." }
   ```
   `WorldService` creates the `Sky` in `Lighting` and hides the sun, moon and stars so they don't sit on top of the painted sky.
3. Or do it by hand: insert a `Sky` into `Lighting`, paste each id into the matching property, and set `CelestialBodiesShown` off.

Match the lighting to the sky: warm sunset → `Lighting.ClockTime ≈ 17.5` and a warm `OutdoorAmbient`; pastel day → `ClockTime 14`, `Atmosphere` density about 0.3 with a colour from the horizon. If you add an `Atmosphere`, keep its `Haze` low, or it washes out the custom sky.

If a seam or face looks rotated in Studio, re-run with `--faces` in your own order. Don't edit the mapping in the script; it matches Sloyd's tested export.
