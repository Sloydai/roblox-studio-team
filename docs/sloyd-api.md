# Sloyd API rules for every skill in this team

Source of truth: Sloyd's API docs (`api-dashboard/documentation/` in Sloydai/Horizon, published at https://www.sloyd.ai/api). If anything here disagrees with a live tool schema, the tool schema wins.

## Connection

The plugin ships `.mcp.json`, which connects the hosted Sloyd MCP server using env vars:

```bash
export SLOYD_CLIENT_ID=sok_live_...
export SLOYD_CLIENT_SECRET=...        # shown once in the API Dashboard; never commit it
```

Manual setup (same thing):

```bash
claude mcp add --transport http sloyd https://api.sloyd.ai/api/mcp \
  --header "x-client-id: $SLOYD_CLIENT_ID" \
  --header "x-client-secret: $SLOYD_CLIENT_SECRET"
```

Never print, echo, log or write the secret into any file. Never put it in a command's arguments.

## Tools (the only ones that exist)

| Tool | Used by | Cost (credits) |
|---|---|---|
| `get_credit_balance` | everyone, before spending | 0 |
| `get_generation_styles` | game-designer | 0 |
| `generate_3d_from_text` | prop-modeler | 25 textured (10 mesh + 5 text + 10 texture) |
| `generate_3d_from_image` | prop-modeler (concept-art route) | 20 textured |
| `generate_3d_from_images` | prop-modeler (multi-view) | 30 textured, +5 quads |
| `upload_image` | prop-modeler, world-backdrop | 0 |
| `generate_image` | game-designer (concept art), prop-modeler | 10 |
| `edit_image` | game-designer | 15 |
| `retexture_model` | skin-variants | 15 |
| `split_model_into_parts` | prop-modeler (optional) | 40 |
| `generate_skybox` | world-backdrop | 25 |
| `generate_skybox_from_image` | world-backdrop | 25 |
| `edit_skybox` | world-backdrop | 25 |
| `get_job` | everyone | 0 |

Prices: https://www.sloyd.ai/api/pricing (USD 1 = 75 credits; 3D adds +10 at 500K+ faces). Re-check that page if a 402 reports a different `required` value.

Not available to public API keys (do not call, do not imitate): Roblox avatar creator, selfie-to-Roblox avatar, Roblox account upload / Studio-plugin queue, auto-rig, animation, spritesheets. Treat them as "coming soon".

## Job flow

1. A generation tool returns `jobId` immediately.
2. Call `get_job` with `{ "jobId": ..., "wait": 30 }` until `done` is `true`.
3. `status: "success"` → `outputs.glbUrl` (3D), `outputs.imageUrl` (image), `outputs.panoramaUrl` + `outputs.cubemapFaceUrls` (skybox). `status: "error"` → read `errorMessage`; credits are refunded automatically.
4. Download GLBs with `curl -fsSL -o <path> <glbUrl>`. The URL is public, no auth.

Always record every `jobId` in `roblox-assets/manifest.json` as soon as you get it. There is no list-jobs endpoint, so a lost id is a lost asset.

## Spending rules

- Before any batch: call `get_credit_balance`, add up the batch cost from the table, show the user `N jobs, X credits (~$Y), balance B`, and get a yes before submitting.
- At most **5 jobs in flight** per key. Submit 5, poll, submit the next as each finishes.
- **402** `Payment Required`: nothing was charged. Report `required` vs `available`, point to https://api-dashboard.sloyd.ai, stop the batch. Don't retry in a loop.
- **429**: you already have 5 jobs running. Wait for one to finish (`get_job` with `wait: 30`), then retry the same request.
- **422**: a parameter is wrong. Fix it from the error message; never guess new parameter names.
- **401**: keys are missing or revoked. Ask the user to check `SLOYD_CLIENT_ID` / `SLOYD_CLIENT_SECRET`.

## Parameters that matter for Roblox

- `generate_3d_from_text`: `prompt`, `genStyleId` (e.g. `Roblox`, `CozyMobile`, `Cartoon`, `Polygonal`), `topology: "triangles"`, `targetFaceCount` (ask for the asset's triangle budget so it arrives under Roblox's 20,000 limit), `textureResolution: "1k"` (the exporter then sizes textures to Roblox's guidance: 256 px for ~5-stud props, 512 for ~10, 1024 for ~20).
- `retexture_model`: `jobId` of a model you own, `prompt`, `textureResolution: "1k"`.
- `generate_skybox`: `prompt`, `genStyleId`.

## REST fallback

If the MCP server isn't connected, use `${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py`. It speaks the same REST API (`https://api.sloyd.ai/api`), reads the same env vars, and enforces the same rules:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py balance
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py estimate roblox-assets/plan.json
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py run roblox-assets/plan.json --out roblox-assets
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sloyd_api.py job <jobId> --wait
```
