# Candy Climb: the launch demo

The team's real run for "obby in a candy world", on 2026-11-04. 11 Sloyd jobs, 245 credits (balance 415 → 170). All 11 succeeded on the first try.

## What it made

| Asset | Role | Triangles | Size (studs, X×Y×Z) | Texture | Sloyd job |
|---|---|---|---|---|---|
| GumdropPlatform | platform | 3,000 | 9.96 × 2.5 × 10.0 | 512 | `4lbmlnci` |
| WrappedCandy | collectible | 784 | 2.5 × 0.96 × 0.8 | 256 | `vxxhjvam` |
| CupcakeCheckpoint | checkpoint | 4,000 | 4.51 × 6.0 × 4.51 | 512 | `gg7xqu0g` |
| LollipopTree | decor | 3,000 | 8.01 × 16.0 × 8.01 | 1024 | `g7j5uuwj` |
| GiantCake | finish | 11,999 | 13.71 × 12.0 × 13.71 | 1024 | `gai4ysca` |
| CandyShopStand | shop | 8,000 | 9.57 × 9.0 × 8.52 | 512 | `g9dp2s3c` |
| CandyBackpack (Classic, free) | cosmetic | 2,500 | 1.64 × 2.5 × 2.06 | 256 | `sdmxlt64` |
| CandyBackpack_Mint (15 coins) | cosmetic | 2,500 | same | 256 | `iv4zq3m4` |
| CandyBackpack_Chocolate (30) | cosmetic | 2,500 | same | 256 | `7928gabp` |
| CandyBackpack_Galaxy (60) | cosmetic | 2,500 | same | 256 | `wg1m6q9d` |
| Sky (6 faces, 1024 px) | sky | none | none | 1024 | `n0bbe2c3` |

- Sloyd honoured every `targetFaceCount`, so no decimation was needed. The exporter cut textures from 1024–2048 px down to Roblox's size guidance, set studs and a ground pivot, and verified every FBX, OBJ and GLB by re-importing it.
- Previews: `roblox-assets/previews/` (`props_sheet.png`, `skins_sheet.png`). Sky faces: `roblox-assets/sky/` (`preview_cross.png`).
- Game: `roblox-game/` is the Rojo kit with these real sizes in `GameConfig.luau`. It builds to `roblox-game/SloydGame.rbxlx` and type-checks with 0 errors.
- Raw GLBs aren't committed. Each one is at `https://storage.googleapis.com/ai-services-quality/jobs/<jobId>.glb`.

## Play it in Studio (needs Windows or macOS)

1. Open `roblox-game/SloydGame.rbxlx` and press Play. The course works with placeholder blocks.
2. File → Import every `roblox-assets/export/*/*.fbx` (Scale Unit: Stud, Merge Meshes on).
3. View → Command Bar, then paste `roblox-game/studio/SetupImportedAssets.luau`.
4. Asset Manager → Bulk Import `roblox-assets/sky/Skybox*.png`, then put the ids in `GameConfig.Sky`.
5. Press Play again.

## Re-run it

```bash
python3 ../../scripts/sloyd_api.py run roblox-assets/plan.json --out roblox-assets   # resumes from run_state.json
python3 ../../scripts/roblox_mesh.py batch roblox-assets/manifest.json
python3 ../../scripts/roblox_sky.py --job roblox-assets/sky/sky_job.json --out roblox-assets/sky
```

Delete `roblox-assets/run_state.json` to generate fresh assets (costs 245 credits again).
