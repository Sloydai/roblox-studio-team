# Roblox Studio Team for Claude Code

Seven Claude skills that take a Roblox game idea to a playable place with custom 3D assets. Sloyd generates the models, shop skins and skybox. The team makes them pass Roblox's limits, writes the Luau, and walks you through Studio and Rojo.

```
/roblox-studio:roblox-producer obby in a candy world
```

→ a design doc, 7 Roblox-ready props (FBX/OBJ/GLB under 20,000 triangles, sized in studs), 3 shop skins, a six-face Sky, and a Rojo project that builds to a `.rbxlx` you can press Play on.

## The team

```
               roblox-producer (orchestrates, budgets credits, checks every hand-off)
                                     │
 game-designer ──plan.json──► prop-modeler ──manifest.json──► skin-variants
       │                           │                               │
       └──skybox prompt──► world-backdrop          luau-scripter ◄─┘
                                   │                      │
                                   └──► studio-importer ◄─┘  (import, Rojo, playtest)
```

| Skill | Does | Sloyd tools |
|---|---|---|
| `game-designer` | Turns an idea into a one-page design doc and `plan.json`: prompts, stud sizes, triangle budgets, collision, skins and prices | `get_generation_styles`, optional `generate_image` |
| `prop-modeler` | Generates every asset in one style, then decimates, rescales, re-pivots and exports with checks | `generate_3d_from_text` / `_image` / `_images`, `get_job` |
| `skin-variants` | Retextures a base item into shop skins with a price ladder | `retexture_model` |
| `world-backdrop` | Generates a skybox and converts it into Roblox `Sky` faces | `generate_skybox`, `generate_skybox_from_image`, `edit_skybox` |
| `luau-scripter` | Fills a tested Rojo kit: course builder, collectibles, checkpoints, DataStore, shop, dev products | none |
| `studio-importer` | Importer settings, collision fidelity, Rojo setup and sync, playtest checklist | none |
| `roblox-producer` | Runs the pipeline, gets your OK on cost, stops on any failed gate | `get_credit_balance` |

## Install

```bash
# 1. Sloyd API key: https://api-dashboard.sloyd.ai -> API Keys, then add credits (minimum $12 = 900 credits)
export SLOYD_CLIENT_ID=sok_live_...
export SLOYD_CLIENT_SECRET=...

# 2. Plugin (bundles the Sloyd MCP server, which reads the two env vars above)
claude plugin marketplace add Sloydai/roblox-studio-team
claude plugin install roblox-studio@sloyd-roblox-studio-team
```

Inside Claude Code you can use `/plugin marketplace add Sloydai/roblox-studio-team` and `/plugin install roblox-studio@sloyd-roblox-studio-team` instead.

To connect Sloyd without the plugin's bundled config:

```bash
claude mcp add --transport http sloyd https://api.sloyd.ai/api/mcp \
  --header "x-client-id: $SLOYD_CLIENT_ID" --header "x-client-secret: $SLOYD_CLIENT_SECRET"
```

### Requirements

| Tool | Why | Required |
|---|---|---|
| Claude Code | runs the skills | yes |
| Sloyd API key + credits | generation | yes |
| Blender 3.6+ (free) | decimation and FBX export, run headless | yes, for prop-modeler and skin-variants |
| Python 3.9+ | the scripts (mesh and API scripts use only the standard library) | yes |
| Pillow + NumPy | sky conversion (`scripts/requirements.txt`) | for world-backdrop |
| Rojo 7.7 (`rokit install`) | build and live-sync the game | recommended |
| Roblox Studio | play and publish | yes |

## What a run costs

| Item | Credits |
|---|---|
| Textured 3D model (text) | 25 |
| Shop skin (retexture) | 15 |
| Skybox | 25 |
| Concept image (optional) | 10 |

The example below is 7 models, 3 skins and 1 sky: 245 credits, about $3.27. The producer shows the total against your balance and waits for a yes before spending anything. Prices: https://www.sloyd.ai/api/pricing.

## Roblox details the team handles

- **20,000 triangles per MeshPart.** It asks Sloyd for each asset's budget (`targetFaceCount`), then decimates anything still over it in Blender. Vertices are welded first, so decimation can't open holes along UV seams. Every exported file is re-imported and checked.
- **Texture size by stud size**, following Roblox's guidance: 256 px for about 5 studs, 512 for 10, 1024 for 20.
- **Studs, not meters.** 1 unit = 1 stud, so the Importer's default Scale Unit (Stud) gives the right size. FBX uses Roblox's Blender export settings (Z forward, Y up, FBX Unit Scale).
- **Ground pivot.** The origin is at bottom-center, so `PivotTo` puts models on the floor.
- **CollisionFidelity by role.** PreciseConvexDecomposition for platforms, Hull for decor, Box for pickups. It's set by a Studio Command Bar script, because game scripts can't set it.
- **Sky orientation.** Uses the same face mapping as Sloyd's own Roblox cubemap export.
- **Game code that runs before the art exists.** The kit spawns sized placeholders until the imported model of the same name appears in `ReplicatedStorage.Assets`.
- **Safe saving and purchases.** A failed DataStore load never overwrites data, `BindToClose` flushes saves, and `ProcessReceipt` grants each purchase once.

## Files a run creates in your project

```
roblox-assets/
  design-doc.md        game-designer
  plan.json            game-designer -> prop-modeler, skin-variants, world-backdrop
  manifest.json        every jobId, file and export check result
  raw/*.glb            Sloyd downloads
  export/<Name>/       <Name>.fbx .obj .glb textures/ <Name>.report.json
  previews/*.png       renders for review
  sky/                 SkyboxBk/Dn/Ft/Lf/Rt/Up.png, preview_cross.png, sky.json
roblox-game/           Rojo project (from templates/rojo-game)
```

## This repo

```
.claude-plugin/        plugin.json, marketplace.json, icon
.mcp.json              Sloyd MCP server (env-var headers, no secrets)
skills/                the 7 skills
docs/                  sloyd-api.md (API rules), roblox-reference.md (limits)
scripts/
  roblox_mesh.py       check / process / batch / preview (Blender headless)
  blender_roblox.py    Blender worker
  roblox_sky.py        Sloyd skybox -> Roblox Sky faces
  sloyd_api.py         REST fallback: balance, estimate, run a plan (max 5 concurrent)
  tests/               unit tests
templates/rojo-game/   Luau kit + Studio setup script
examples/candy-climb/  the demo run
```

### Tests

```bash
BLENDER=/path/to/blender python3 -m unittest discover -s scripts/tests -v
```

There are 9 tests:
- **Mesh** (needs Blender): an 81k-triangle, 2048 px test sphere is reduced to 18,000 or fewer triangles, scaled to 6 studs and exported to FBX, OBJ and GLB. Each file is re-imported and checked, including for holes. A real Sloyd model (CC BY 4.0, from Sloyd's free library) goes from 39,200 to under 18,000 triangles.
- **Sky**: the panorama-to-faces conversion round-trips through a port of Sloyd's stitcher (mean error under 2/255). Face directions and the Roblox mapping are also checked.

The Luau kit builds with Rojo 7.7.1 and type-checks with `luau-lsp analyze` against Roblox definitions, with zero errors.

## Coming soon

Sloyd has a Roblox avatar creator, selfie-to-Roblox-avatar and one-click upload to your Roblox account in its web app. These aren't available to public API keys yet, so this team doesn't use them and doesn't imitate them. It makes props, worn cosmetics and skies.

## Security and privacy

- Keys stay in environment variables. `.mcp.json` only references `${SLOYD_CLIENT_ID}` and `${SLOYD_CLIENT_SECRET}`. Never commit them.
- Prompts and generated assets are processed by Sloyd: https://www.sloyd.ai/privacy-policy.

## License

MIT
