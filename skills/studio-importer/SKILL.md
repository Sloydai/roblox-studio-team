---
name: studio-importer
description: Use when the user is importing models into Roblox Studio or setting up Rojo. Examples are "how do I add this FBX to Roblox", "my model imported huge, tiny or rotated", "set up Rojo" or "what MeshPart settings do I need". Gives step-by-step 3D Importer settings, collision fidelity, asset registration, Sky uploads, Rojo build and live sync, DataStore and monetization settings, and a playtest checklist.
---

# Studio Importer

You walk the user through Studio, because you can't click in it for them. Give exact menu paths and values, one step at a time, and say what they should see after each step. Sloyd's direct Roblox upload and Studio plugin queue need a signed-in Sloyd web account, not an API key. For API users that path is "coming soon", so use the manual import below.

Reference: `${CLAUDE_PLUGIN_ROOT}/skills/studio-importer/references/roblox-reference.md`.

## A. Open the place

Option 1, Rojo (recommended, keeps code in git):
1. Install Rokit (github.com/rojo-rbx/rokit), then run `rokit install` inside `roblox-game/`. Or install Rojo 7.7.x another way.
2. In Studio, install the **Rojo** plugin from the Creator Store (match the CLI version).
3. `rojo build default.project.json -o SloydGame.rbxlx`, then open `SloydGame.rbxlx` in Studio. Save it to Roblox with File → Publish to Roblox.
4. For live editing, run `rojo serve` in `roblox-game/`, then Plugins → Rojo → **Connect**. Code edits now sync into Studio. Rojo manages `ReplicatedStorage.Shared`, `ServerScriptService.Server` and `StarterPlayerScripts.Client`; it leaves `ReplicatedStorage.Assets` alone (`$ignoreUnknownInstances`).

Option 2, no Rojo: open the `.rbxlx` that luau-scripter built. To change code later, edit the scripts in Studio.

Press **Play** now. The course works with placeholder blocks. That's expected.

## B. Import the models

For each `roblox-assets/export/<Name>/<Name>.fbx` (FBX keeps embedded textures; `.glb` also works):

1. **File → Import** (or Home → Import 3D), then select the file. You can multi-select.
2. In the Importer:
   - **File Geometry → Scale Unit: Stud**. The exporter already wrote studs, so keep the default.
   - **File General → Set Pivot to Scene Origin: on** (default). The exporter put the origin at bottom-center.
   - **Merge Meshes**: on for single-texture props, so you get one MeshPart.
   - **Upload to Roblox: on**, so meshes and textures become assets you can publish.
   - The preview should show the model the right way up, at the size in its report (for example GumdropPlatform about 10×3×10). Warnings about non-manifold geometry are worth reading. Triangle-count errors should never appear, because every file is pre-checked under 20,000 per mesh.
3. Click **Import**. The asset lands in Workspace, named after the file.

If an asset faces the wrong way, rotate it 180° on Y in Studio. Don't re-export.

## C. Register the assets

1. Open **View → Command Bar**.
2. Paste the contents of `roblox-game/studio/SetupImportedAssets.luau` (or `${CLAUDE_PLUGIN_ROOT}/skills/luau-scripter/templates/rojo-game/studio/SetupImportedAssets.luau` with `ROLES` edited), then press Enter.
3. Output prints `moved N assets into ReplicatedStorage.Assets` and lists any missing names.

The script sets **CollisionFidelity** per role: PreciseConvexDecomposition for platforms and the finish, Hull for checkpoints, shop and decor, Box for collectibles and cosmetics. It also anchors the props. Game scripts can't change CollisionFidelity, which is why this runs in Studio.

Press **Play**. Placeholders are replaced by the Sloyd models.

## D. Sky

Follow world-backdrop step 4: Asset Manager → Bulk Import the six PNGs, then put the ids in `GameConfig.Sky` (or set them on a `Sky` in `Lighting` by hand).

## E. Services and monetization

- **Game Settings → Security → Enable Studio Access to API Services**: on, or DataStores fail in Studio. The game still runs, but nothing saves.
- Developer products: Creator Dashboard → your experience → Monetization → Developer Products. Put the ids in `GameConfig.Shop.coinProducts`. Test purchases in Studio are free.
- Before publishing, set the experience's maturity questionnaire and devices in Creator Dashboard.

## F. Playtest checklist

- Spawn → jump the first five platforms with the default character. Every gap is clearable.
- Touch a collectible: the Coins leaderstat goes up and the collectible respawns after the configured delay.
- Reach a checkpoint, reset (Esc → Reset), and you respawn there.
- Fall to the kill floor and you respawn at your last checkpoint.
- Reach the finish: a toast appears and coins are added once.
- Open the shop with the ProximityPrompt: buy a skin with enough coins, get rejected without, equip, reset, and the skin is still on your back.
- **Test → Device**: phone emulation keeps the shop readable and stays above 30 FPS with all props on screen.
- Stop, Play again: coins and owned skins persisted (API access on).

Report the result of each line to the user. For anything failing, give the exact property or Config value to change.
