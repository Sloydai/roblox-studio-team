# Roblox Studio Team

A Roblox game studio for your coding agent. Describe your game once and get a playable Roblox place:
- a design doc
- custom 3D props that pass Roblox's limits
- shop skins
- a custom sky
- Luau game code, ready for Rojo or for Studio directly

Built for Roblox creators. Powered by the [Sloyd API](https://www.sloyd.ai/api).

![7 candy obby props made by the Roblox Studio Team skills](examples/candy-climb/images/props-sheet.png)

*A real run: 7 props, 3 backpack skins and a skybox for a candy obby, 11 Sloyd jobs for 245 credits (~$3.27), and all 10 meshes ready for Studio. [See the run](examples/candy-climb/).*

```
/plugin marketplace add Sloydai/roblox-studio-team
/plugin install roblox-studio@sloyd-roblox-studio-team
```

## The team

```
roblox-studio/
├── roblox-producer   runs the whole pipeline from one prompt, with budget gates
├── game-designer     idea → design doc + plan.json (prompts, studs, triangle budgets, prices)
├── prop-modeler      Sloyd 3D → under 20k triangles, studs, ground pivot, verified FBX/OBJ/GLB
├── skin-variants     retexture → shop skins with a price ladder
├── world-backdrop    Sloyd skybox → the six faces of a Roblox Sky
├── luau-scripter     tested Rojo kit: course, collectibles, checkpoints, DataStore, shop, dev products
├── studio-importer   3D Importer settings, CollisionFidelity, Rojo sync, playtest checklist
└── sloyd-api         shared plumbing: credentials, credits, job polling, errors, REST fallback
```

Each role hands its output to the next:

1. game-designer writes `design-doc.md` and `plan.json`
2. prop-modeler generates the props and writes `manifest.json` plus `export/<Name>/`
3. skin-variants retextures the cosmetic and adds the skins to the manifest
4. world-backdrop turns the skybox into `sky/Skybox*.png`
5. luau-scripter fills `GameConfig.luau` from the manifest, and `rojo build` makes the place
6. studio-importer walks you through import, Rojo and a playtest

## What you get

```
roblox-assets/
├── design-doc.md      pitch, loop, economy, art direction, asset table, cost
├── plan.json          every asset: prompt, role, studs, triangle budget, collision; skins; sky
├── manifest.json      every asset: jobIds, files, triangle counts, export checks
├── export/<Name>/     <Name>.fbx .obj .glb + textures/ + <Name>.report.json
├── previews/          renders of every asset
└── sky/               SkyboxBk/Dn/Ft/Lf/Rt/Up.png, preview_cross.png, sky.json
roblox-game/           Rojo project; `rojo build` → SloydGame.rbxlx
```

## Setup

1. **Get your own Sloyd API key.** Each user brings their own credentials, and generations are billed to your prepaid credits.
   1. Go to [api-dashboard.sloyd.ai](https://api-dashboard.sloyd.ai), open **API Keys**, and click **Generate Key**. Copy the secret; it's shown once.
   2. Buy credits under **Usage & Billing**. The minimum is $12 for 900 credits.
2. **Export the key** in the shell you start your agent from, or copy `.env.example` to a git-ignored `.env`.

   ```bash
   export SLOYD_CLIENT_ID="sok_live_..."
   export SLOYD_CLIENT_SECRET="..."
   ```

3. **Install the plugin** (above). It registers Sloyd's hosted MCP server (`https://api.sloyd.ai/api/mcp`) using those two environment variables. To add the server by hand instead:

   ```bash
   claude mcp add --transport http sloyd https://api.sloyd.ai/api/mcp \
     --header "x-client-id: $SLOYD_CLIENT_ID" \
     --header "x-client-secret: $SLOYD_CLIENT_SECRET"
   ```

Other agents (Cursor, VS Code, Codex and others) can load the `skills/` folders directly. Clients without MCP can use the bundled standard-library Python client or curl (`skills/sloyd-api/references/rest-fallback.md`). Credentials are only read from the environment and never written to any file.

## Example prompts

- `Make me a Roblox obby in a candy world. Budget 300 credits.`
- `Design a pet simulator and give me the asset list with triangle budgets before spending anything.`
- `Generate a treasure chest prop for Roblox, under 5,000 triangles, 4 studs tall.`
- `This FBX is 60k triangles. Make it import into Studio.`
- `Give my backpack Mint, Chocolate and Galaxy skins and put them in the shop for 15, 30 and 60 coins.`
- `Make a sunset sky for my game and set it up as a Roblox Sky.`
- `Add a tycoon dropper system to my Rojo project.`
- `Walk me through importing these FBX files and setting up Rojo.`

## Cost

Sloyd API credits ($1 = 75 credits). The agent always shows the estimate and your balance before spending.

| Step | Credits |
|---|---|
| Text to 3D (textured) | 25 |
| Image to 3D (textured) | 20 |
| Concept image | 10 |
| Shop skin (retexture) | 15 |
| Skybox | 25 |
| Split into parts | 40 |

The launch game was planned at 245 credits (7 props, 3 skins, 1 sky) and came in at exactly 245, with no failed jobs and no rerolls. Full breakdown: [examples/candy-climb](examples/candy-climb/README.md). Current prices: [sloyd.ai/api/pricing](https://www.sloyd.ai/api/pricing).

## Roblox details the team handles

- **20,000 triangles per MeshPart.** Each asset's budget is sent to Sloyd as `targetFaceCount`, and anything still over it is decimated in Blender. Vertices are welded first, so decimation can't open holes along UV seams. Every exported file is re-imported and checked.
- **Textures sized by studs,** following Roblox's guidance: 256 px for about 5 studs, 512 for 10, 1024 for 20.
- **Studs, not meters.** 1 unit = 1 stud, so the Importer's default Scale Unit (Stud) is right. FBX uses Roblox's Blender settings (Z forward, Y up, FBX Unit Scale).
- **Ground pivot.** The origin is at bottom-center, so `PivotTo` puts props on the floor.
- **CollisionFidelity by role.** PreciseConvexDecomposition for platforms, Hull for decor and Box for pickups. A Studio Command Bar script sets it, because game scripts can't.
- **Sky orientation.** Uses the same face mapping as Sloyd's own Roblox cubemap export.
- **Code that runs before the art exists.** The kit spawns sized placeholders until a model with the same name is in `ReplicatedStorage.Assets`.
- **Safe saving and purchases.** A failed DataStore load never overwrites data, `BindToClose` flushes saves, and `ProcessReceipt` grants each purchase once.

## Example: Candy Climb (candy obby)

[`examples/candy-climb/`](examples/candy-climb/) is the real output of one run:

- the design doc and the plan
- a run record with the prompts, triangle counts, stud sizes, texture sizes and spend
- renders of every prop and skin, and the sky as a cross preview
- the Roblox `IMPORT.md` and the filled-in `GameConfig.luau`
- the 3D models aren't included: run the plan with your own Sloyd key to make them

## Requirements

- Python 3.9+ for the helper scripts. The mesh and API scripts use the standard library only. The sky converter needs Pillow and NumPy (`skills/world-backdrop/scripts/requirements.txt`).
- Blender 3.6+ (free), run headless for decimation and FBX export
- A Sloyd API key with credits
- Roblox Studio
- Optional: Rojo 7.7 (`rokit install` in the Rojo project), and `luau-lsp` for type checks

## Tests

```bash
BLENDER=/path/to/blender python3 -m unittest discover -s skills/prop-modeler/scripts -p "test_*.py" -v
python3 -m unittest discover -s skills/world-backdrop/scripts -p "test_*.py" -v
```

- **Mesh tests** (need Blender): an 81k-triangle, 2048 px test sphere is decimated to 18,000 or fewer triangles, scaled to 6 studs and exported to FBX, OBJ and GLB. Each file is re-imported and checked for its triangle count, texture size and holes. Set `ROBLOX_TEST_MODEL=/path/to/model.glb` to also run the test on a real Sloyd model.
- **Sky tests:** the panorama-to-faces conversion round-trips through a port of Sloyd's stitcher. Face directions and the Roblox mapping are checked too.

The Luau kit builds with Rojo 7.7.1 and type-checks with `luau-lsp analyze` against the Roblox definitions, with 0 errors.

## Coming soon

Sloyd's web app has a Roblox avatar creator, selfie-to-Roblox-avatar and one-click upload to your Roblox account. These aren't available to public API keys yet, so this team doesn't use or imitate them. It makes props, worn cosmetics and skies.

## Privacy

Prompts and images you send are processed by Sloyd. See the [Sloyd privacy policy](https://www.sloyd.ai/privacy-policy).

## License

MIT
