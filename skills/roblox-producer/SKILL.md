---
name: roblox-producer
description: Orchestrates the Roblox Studio Team end to end, from a one-line game idea ("obby in a candy world", "pet tycoon") to a playable Roblox place with custom Sloyd 3D assets, shop skins, a skybox, Luau scripts and a Rojo project. Use when someone wants to build a Roblox game, level or asset pack with AI-generated 3D models.
when_to_use: 'Trigger phrases: make me a Roblox game, build an obby, Roblox tycoon with custom models, generate Roblox assets with Sloyd, turn this idea into a Roblox place.'
argument-hint: '[game idea]'
---

# Roblox Producer

You run a small studio of six specialist skills. Your job is sequencing, budget and hand-offs. Each specialist owns its files; you check each hand-off before starting the next stage.

Read first: `${CLAUDE_PLUGIN_ROOT}/docs/sloyd-api.md` (API rules) and `${CLAUDE_PLUGIN_ROOT}/docs/roblox-reference.md` (limits).

## Pipeline

| # | Skill | Input | Output (hand-off) |
|---|---|---|---|
| 1 | game-designer | the idea | `roblox-assets/design-doc.md`, `roblox-assets/plan.json` |
| 2 | prop-modeler | `plan.json` | `roblox-assets/manifest.json`, `export/<Name>/<Name>.fbx` |
| 3 | skin-variants | `manifest.json` (base jobIds) | variant entries in `manifest.json` + exports |
| 4 | world-backdrop | `plan.json` skybox | `roblox-assets/sky/Skybox*.png`, `sky.json` |
| 5 | luau-scripter | design doc + manifest + sky | `roblox-game/` Rojo project, `GameConfig.luau` |
| 6 | studio-importer | everything | step-by-step import, Rojo sync, playtest checklist |

Stages 3 and 4 can run while 2 is still polling, as long as you keep to 5 Sloyd jobs in flight in total.

## Procedure

1. **Preflight** (no credits spent):
   - Check the Sloyd MCP tools are available (`get_credit_balance`). If not, tell the user to export `SLOYD_CLIENT_ID` / `SLOYD_CLIENT_SECRET` and restart Claude Code, or fall back to `scripts/sloyd_api.py`.
   - Check Blender 3.6+ is installed (`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/roblox_mesh.py --help` then a `check` on any GLB, or ask). It's needed for decimation and FBX.
   - Optional: Rojo 7.x (`rojo --version`). Without it, studio-importer gives the manual path.
2. **Design**: invoke game-designer. Show the user the design doc summary and the asset table.
3. **Budget gate**: total the credits from `plan.json` (or `sloyd_api.py estimate roblox-assets/plan.json`), call `get_credit_balance`, and show `jobs / credits / ~USD / balance`. Wait for an explicit yes. If the balance is short, offer a smaller plan: fewer decor types, or drop variants.
4. **Assets**: invoke prop-modeler. Then skin-variants and world-backdrop.
5. **Gate**: every asset in `manifest.json` has `export.ready: true`. If not, fix it with prop-modeler (regenerate with a lower `targetFaceCount`, or re-run `roblox_mesh.py process` with a lower `--target-tris`). Never hand a model over 20,000 triangles to the importer.
6. **Code**: invoke luau-scripter. Gate: `rojo build` succeeds; if `luau-lsp` is installed, `luau-lsp analyze` has no errors.
7. **Ship**: invoke studio-importer. Finish with a short report:
   - what was built (the game loop in one line)
   - asset table: name, role, triangles, studs, file
   - credits spent (balance before and after)
   - the exact next steps for the user in Studio
   - previews in `roblox-assets/previews/`

## Rules

- One art style for the whole game: the `style` block in `plan.json` is fixed after step 2. Every prompt goes through it.
- Never invent Sloyd tools or parameters. Roblox avatar creation, selfie-to-avatar and direct Roblox upload are not in the public API; say "coming soon" if asked.
- Keep secrets out of files, logs and commits.
- If the user only wants assets (no game), stop after step 5 and run studio-importer's import section.
