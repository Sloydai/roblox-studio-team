---
name: skin-variants
description: Creates cosmetic and shop-item variants of a Roblox asset with Sloyd's retexture_model (same mesh, new texture), exports them Roblox-ready and adds them to the game's shop with prices. Use for skins, colourways, seasonal or limited items, and anything sold for coins or Robux.
when_to_use: 'Trigger phrases: make skins for my item, shop variants, colour variants, limited edition version, monetize with cosmetics.'
argument-hint: '[base asset name] [variant ideas]'
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/roblox_mesh.py *)
---

# Skin Variants

Cosmetics are how most Roblox games earn without being pay-to-win. Retexturing keeps the mesh, so every variant has the same silhouette, triangle count and fit as the base, and only the look changes.

Read `${CLAUDE_PLUGIN_ROOT}/docs/sloyd-api.md`.

## Inputs

- `roblox-assets/manifest.json` with the base asset's finished `jobId` (made by prop-modeler). Retexture only works on a job you own.
- `plan.json` → `variants[]`, or the user's ideas.
- For an external model, upload it first with REST `POST /jobs/upload-3d` (free) and use the returned `jobId`. There's no MCP tool for this, so use curl with the env-var headers, as in sloyd-api.md.

## 1. Design the ladder

Price variants so there's a free starter, a cheap first purchase, and something to grind for:

| Tier | Example | Coins |
|---|---|---|
| Starter | Classic (the base) | 0 |
| Common | Mint Swirl | 10–20 |
| Rare | Choco Fudge | 30–50 |
| Epic / limited | Galaxy Gummy, seasonal | 60–150 |

Each variant prompt names a material and a palette, not a new shape: "mint green and white peppermint swirl, glossy hard candy". Shape words are ignored, because the mesh is fixed.

## 2. Retexture (15 credits each, max 5 in flight)

Check `get_credit_balance` first. Then for each variant:

```json
{ "jobId": "<base jobId>", "prompt": "<variant prompt>, <style.promptSuffix>", "textureResolution": "1k" }
```

Poll `get_job` (`wait: 30`). Download `outputs.glbUrl` to `roblox-assets/raw/<Base>_<Variant>.glb`. Add a manifest entry that copies the base's `role`, `heightStuds`, `triBudget` and `collision`, and adds `"variantOf": "<Base>"`, `displayName`, `price` and the new `jobId`.

## 3. Export and check

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/roblox_mesh.py batch roblox-assets/manifest.json --only <Base>_Mint,<Base>_Chocolate
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/roblox_mesh.py preview roblox-assets/export/<Base>_Mint/<Base>_Mint.glb --out roblox-assets/previews/<Base>_Mint.png
```

Use the same `heightStuds` as the base so every skin attaches at the same offset.

## 4. Wire into the shop

Give luau-scripter (or edit directly) `GameConfig.Shop.skins`:

```lua
{ id = "Mint", displayName = "Mint Swirl", asset = "CandyBackpack_Mint", price = 15 },
```

The shop server validates price and ownership, saves owned and equipped skins in the DataStore, and re-attaches the equipped skin on respawn.

## Robux

- Coin packs: developer products in `GameConfig.Shop.coinProducts`, granted idempotently in `ProcessReceipt`.
- To sell a skin directly for Robux, create a Game Pass, then check `MarketplaceService:UserOwnsGamePassAsync` and grant `owned[id] = true` on join. Tell luau-scripter.
- Selling items on the Avatar Marketplace (UGC) has separate account requirements and Roblox's accessory specs. Retextured props aren't automatically UGC-ready.
