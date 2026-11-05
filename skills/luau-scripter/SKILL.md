---
name: luau-scripter
description: Writes the Luau game code that places and wires the team's Sloyd assets into a playable Roblox game, starting from a tested Rojo kit (obby course builder, collectibles with respawn, checkpoints, finish reward, kill floor, DataStore saving, cosmetic shop with server-side validation, Robux coin packs, custom Sky). Use to script a Roblox game around generated assets, or to add systems such as spawners, shops, collectibles or tycoon droppers.
when_to_use: 'Trigger phrases: write the Roblox scripts, wire up the assets, Luau for my obby, add a shop, collectible spawner, Rojo project.'
argument-hint: '[feature or design doc]'
---

# Luau Scripter

You write production Luau: `--!strict`, server-authoritative, no deprecated APIs (`wait`, `spawn`, `delay` become `task.*`), and it works before the art is imported.

## 1. Start from the kit

```bash
cp -R ${CLAUDE_PLUGIN_ROOT}/templates/rojo-game ./roblox-game
```

```
roblox-game/
  default.project.json       Rojo tree: Shared -> ReplicatedStorage, Server -> ServerScriptService, Client -> StarterPlayerScripts
  rokit.toml                 pins rojo 7.7.1
  studio/SetupImportedAssets.luau  Command Bar script: moves imports into Assets, sets CollisionFidelity
  src/shared/GameConfig.luau     every number, asset name and price (edit this first)
  src/shared/AssetLibrary.luau   spawn by name: imported model from ReplicatedStorage.Assets, or a sized placeholder
  src/server/Main.server.luau    creates Remotes, starts services
  src/server/DataService.luau    DataStore load/save with retries, no-overwrite on failed load, BindToClose, autosave
  src/server/WorldService.luau   seeded course, collectibles, checkpoints + RespawnLocation, finish, kill floor, decor, Sky
  src/server/ShopService.luau    ProximityPrompt shop, buy/equip validated on server, back-worn cosmetics, ProcessReceipt
  src/client/ShopUI.client.luau       shop window, coin packs, toasts
  src/client/Collectibles.client.luau spin and bob on the client only
```

Placeholders are the key design choice. `AssetLibrary.spawn("GumdropPlatform")` returns the imported model if `ReplicatedStorage.Assets.GumdropPlatform` exists. Otherwise it returns a coloured Part of the configured size. So the place is playable straight after `rojo build`, and imported art drops in by name with no code change.

## 2. Fill `GameConfig.luau` from the hand-offs

- `Config.Assets`: one entry per manifest asset. `size` comes from the exporter report (`export.sizeStuds`, in X/Y/Z order), `role` from the manifest, and a placeholder `color` from the design palette.
- `Config.Course`: stages, gap and rise from the design doc. Keep the edge-to-edge gap at 6 studs or less and `rise` under 4 for default characters (JumpHeight 7.2, WalkSpeed 16).
- `Config.Shop.skins`: from skin-variants (id, displayName, asset, price).
- `Config.Shop.coinProducts`: developer product ids, or leave them at 0 to hide.
- `Config.Sky`: the six `rbxassetid://` values from world-backdrop's `sky.json`, or `nil`.
- Regenerate `ROLES` in `roblox-game/studio/SetupImportedAssets.luau` (the Studio Command Bar setup script) from the manifest names and roles.

## 3. Extend for the design

Add systems as new ModuleScripts in `src/server` with an `init()` called from `Main.server.luau`. Patterns to follow:
- **Server authority**: the client sends intent (an id), and the server checks ownership, price and distance. Never trust client-sent amounts or positions.
- **Remotes** live in `ReplicatedStorage.Remotes`, created by the server. Use RemoteFunctions only for request/response the client waits on.
- **Tags**: `CollectionService` for anything with many instances (collectibles, kill bricks, droppers).
- **Touched** handlers: resolve the player through `Players:GetPlayerFromCharacter`, check `Humanoid.Health > 0`, and debounce per player or per object.
- **Physics flags**: `AssetLibrary.applyRole`. Decor gets `CanTouch = false`, collectibles `CanCollide = false`, cosmetics `Massless`, and everything static is `Anchored`.
- **CollisionFidelity can't be set at runtime**. It's set in Studio by the setup script.
- **Tycoon droppers**: spawn the drop part on the server with a short `Debris:AddItem` lifetime, cap the live drops per plot, and pay on touch with the collector, not by distance.
- **Saving**: add fields to `DataService.Data` and the defaults. Load code must tolerate missing fields from older saves.

## 4. Verify

```bash
cd roblox-game
rojo build default.project.json -o SloydGame.rbxlx
rojo sourcemap default.project.json -o sourcemap.json
luau-lsp analyze --sourcemap=sourcemap.json --definitions=@roblox=globalTypes.d.luau --platform=roblox src   # if installed
```

`globalTypes.d.luau` comes from github.com/JohnnyMorganz/luau-lsp (`scripts/globalTypes.d.luau`). The kit as shipped builds and type-checks with zero errors. Keep it that way.

## Hand-off

`roblox-game/` builds to `SloydGame.rbxlx`. Tell studio-importer which asset names must exist in `ReplicatedStorage.Assets`, and whether DataStores or developer products are used.
