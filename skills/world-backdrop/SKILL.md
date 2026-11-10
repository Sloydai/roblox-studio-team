---
name: world-backdrop
description: Use when a Roblox game needs a custom sky or environment backdrop ("make a sunset sky for my game", "candy land skybox", "change the sky"). Generates a 360 skybox with Sloyd and converts it into the six faces of a Roblox Sky object (SkyboxBk/Dn/Ft/Lf/Rt/Up) with the right orientation, plus matching Lighting settings.
---

# World Backdrop

> **Script paths:** `<skills>` below means the folder this skill is installed in, the parent of this `SKILL.md`'s folder (for example `.agents/skills` or `.claude/skills`). All Roblox Studio Team skills sit side by side there. On Windows, use `python` instead of `python3`.

The sky is the cheapest way to make a Roblox game look like its own place: one job, six images, no triangles.

Load the sloyd-api skill first (credentials, credits, job loop, errors).

## 1. Prompt

Use `plan.json → skybox`, or write one: a horizon, a sky gradient, distant shapes only. Nothing close to the camera, because a sky is infinitely far away and near objects look flat. Match the game's palette and `genStyleId`.

Good: "pastel candy land sky at golden hour, cotton candy clouds, distant lollipop hills on the horizon".
Avoid: characters, text, ground details under the player.

## 2. Generate (25 credits)

`get_credit_balance` first, then `generate_skybox { "prompt": ..., "genStyleId": ... }`. If the user has reference art, upload it with `upload_image` and use `generate_skybox_from_image { "imageJobId": ... }`. For a tweak ("make it night"), use `edit_skybox { "jobId": ..., "prompt": ... }`.

Poll `get_job` (`wait: 30`) until done. Save the full `get_job` result to `roblox-assets/sky/sky_job.json`. Without the MCP server, `python3 <skills>/sloyd-api/scripts/sloyd.py job <jobId> --wait > roblox-assets/sky/sky_job.json` does the same.

## 3. Convert to Roblox faces

```bash
python3 <skills>/world-backdrop/scripts/roblox_sky.py --job roblox-assets/sky/sky_job.json --out roblox-assets/sky
```

Nothing to install with pip: the script uses Pillow and NumPy if they're there, and otherwise runs itself inside Blender (the same Blender prop-modeler uses).

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
