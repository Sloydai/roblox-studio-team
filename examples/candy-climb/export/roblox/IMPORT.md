# Import into Roblox: Candy Climb

The launch run exported 10 meshes as FBX, OBJ and GLB, plus 6 sky faces. The meshes aren't in this repo: run `plan.json` with your own Sloyd key to make them (see the example README). This file shows what you'll get and how to import it.

All files are in studs (1 unit = 1 stud) with a bottom-center pivot. Each was re-imported after export and checked: every mesh is under Roblox's 20,000-triangle limit, with no new holes.

## Steps

1. Studio > File > Import (or Home > Import 3D), then select the `.fbx` files.
2. In the Importer, keep **Scale Unit: Stud** and **Set Pivot to Scene Origin** on, and turn **Merge Meshes** on.
3. View > Command Bar, then paste `skills/luau-scripter/templates/rojo-game/studio/SetupImportedAssets.luau`. It moves the models into `ReplicatedStorage.Assets` and sets CollisionFidelity per role.
4. Asset Manager > Bulk Import the six `Skybox*.png` faces, then put the image ids in `GameConfig.Sky`.
5. Press Play.

## Files

| File | Role | Triangles | Size in studs (x, y, z) | Texture px | CollisionFidelity |
|---|---|---|---|---|---|
| `GumdropPlatform.fbx` | platform | 3,000 | 9.96, 2.50, 10.00 | 512 | PreciseConvexDecomposition |
| `WrappedCandy.fbx` | collectible | 784 | 2.50, 0.96, 0.80 | 256 | Box |
| `CupcakeCheckpoint.fbx` | checkpoint | 4,000 | 4.51, 6.00, 4.51 | 512 | Hull |
| `LollipopTree.fbx` | decor | 3,000 | 8.01, 16.00, 8.01 | 1024 | Hull |
| `GiantCake.fbx` | finish | 11,999 | 13.71, 12.00, 13.71 | 1024 | PreciseConvexDecomposition |
| `CandyShopStand.fbx` | shop | 8,000 | 9.57, 9.00, 8.52 | 512 | Hull |
| `CandyBackpack.fbx` | cosmetic | 2,500 | 1.64, 2.50, 2.06 | 256 | Box |
| `CandyBackpack_Mint.fbx` | cosmetic | 2,500 | 1.64, 2.50, 2.06 | 256 | Box |
| `CandyBackpack_Chocolate.fbx` | cosmetic | 2,500 | 1.64, 2.50, 2.06 | 256 | Box |
| `CandyBackpack_Galaxy.fbx` | cosmetic | 2,500 | 1.64, 2.50, 2.06 | 256 | Box |

The sky is six 1024 px faces: `SkyboxBk`, `SkyboxDn`, `SkyboxFt`, `SkyboxLf`, `SkyboxRt` and `SkyboxUp`.

## Notes

- Sloyd met every triangle budget, so no mesh needed decimating. The exporter shrank textures from 1024–2048 px to Roblox's guidance for each prop's size.
- GiantCake has 21 open edges after export. That's under the warning threshold, and it imports normally.
