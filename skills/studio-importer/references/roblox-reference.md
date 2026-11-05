# Roblox reference for this team

Checked against Roblox creator docs (github.com/Roblox/creator-docs), November 2026.

## Mesh and texture limits

| Limit | Value | Source |
|---|---|---|
| Triangles per mesh (each MeshPart) | 20,000 | art/modeling/specifications |
| Texture size | up to 4096 × 4096; recommended 256 px for ~5-stud objects, 512 for ~10, 1024 for ~20 | art/modeling/texture-specifications |
| Sky face size | square, 1024 px recommended max | Sky docs |
| Import formats | `.fbx`, `.gltf`/`.glb`, `.obj` | studio/importer |
| Geometry | watertight, no zero-thickness, quads/tris | art/modeling/specifications |

A multi-mesh file imports as a `Model` of `MeshPart`s; each MeshPart has its own 20,000 budget and takes one material (one `SurfaceAppearance` or `TextureID`).

## Triangle budgets (what this team targets)

Under 20,000 is the hard rule. For performance on phones (most Roblox players), aim far lower:

| Role | Budget | Why |
|---|---|---|
| collectible (many copies, spinning) | 500–1,500 | dozens on screen |
| cosmetic / backpack / pet | 1,500–4,000 | on every player |
| platform, checkpoint | 2,000–5,000 | repeated 10–30× |
| decor (trees, props) | 2,000–6,000 | repeated |
| hero piece (finish, shop stand, boss) | 8,000–18,000 | one copy |

## Scale

- The Importer's **Scale Unit** defaults to **Stud**. The team's exporter writes 1 unit = 1 stud, so keep the default.
- Default character: about 5 studs tall (R15), WalkSpeed 16, JumpHeight 7.2. Horizontal jump reach is about 8.5 studs. Obby gaps: edge to edge 6 or less, rise under 4.
- Doors at least 6 studs tall and 4 wide; walkable slopes under 89° (MaxSlopeAngle).

## Orientation and pivot

- Roblox is Y-up. The exporter writes FBX with **Z forward, Y up** and **FBX Unit Scale**, as Roblox's Blender guide says. glTF is Y-up by spec.
- The exporter puts the pivot at the **bottom-center** of the model by default. With the Importer's "Set Pivot to Scene Origin" (on by default), `Model:PivotTo(groundCFrame)` sits it on the ground. `AssetLibrary.placeOnGround` places by bounding box, so it works with any pivot.

## Collision

`CollisionFidelity` can only be set in Studio (Properties or the Command Bar), not by game scripts.

| Role | CollisionFidelity |
|---|---|
| platform, finish (players stand on them) | PreciseConvexDecomposition |
| checkpoint, shop, decor | Hull |
| collectible, cosmetic | Box (CanCollide off anyway) |

## Sky

A `Sky` object in `Lighting` takes six image ids: `SkyboxBk`, `SkyboxDn`, `SkyboxFt`, `SkyboxLf`, `SkyboxRt`, `SkyboxUp`. Upload each PNG as an image (Asset Manager → Bulk Import, or the Importer), then use `rbxassetid://<id>`. Set `CelestialBodiesShown = false` so the sun and moon don't float over a painted sky.

## DataStores and monetization

- Studio needs **Game Settings → Security → Enable Studio Access to API Services** for DataStores.
- Developer products: create them in Creator Dashboard → experience → Monetization → Developer Products. Put the id in `GameConfig.Shop.coinProducts`.
- `ProcessReceipt` must return `PurchaseGranted` only after the grant is saved, and must be idempotent by `PurchaseId`.
