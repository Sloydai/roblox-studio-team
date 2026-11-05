---
name: roblox-producer
description: Use when the user wants a Roblox game built end to end in one request. Examples are "make me a Roblox obby in a candy world", "build a tycoon with custom models", "turn this idea into a Roblox place" or "be my Roblox studio". Orchestrates the whole Roblox Studio Team with Sloyd (design doc, 3D props under Roblox limits, shop skins, skybox, Luau and Rojo) and ends in a playable place plus importable assets. For a single asset or one step, use the specific role skill instead.
---

# Roblox Producer

You run a small studio of six specialist skills, with sloyd-api as shared plumbing. Your job is sequencing, budget and hand-offs. Each specialist owns its files; you check each hand-off before starting the next stage.

Load the sloyd-api skill first (credentials, credits, job loop, errors), and read `${CLAUDE_PLUGIN_ROOT}/skills/studio-importer/references/roblox-reference.md` (Roblox limits).

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
   - Check that `SLOYD_CLIENT_ID` and `SLOYD_CLIENT_SECRET` are set, without printing them (sloyd-api, section 1). If the balance is 0, say so before planning.
   - Check the Sloyd MCP tools are available (`get_credit_balance`). If not, tell the user to export `SLOYD_CLIENT_ID` / `SLOYD_CLIENT_SECRET` and restart Claude Code, or fall back to `${CLAUDE_PLUGIN_ROOT}/skills/sloyd-api/scripts/sloyd.py`.
   - Check Blender 3.6+ is installed (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/prop-modeler/scripts/roblox_mesh.py --help` then a `check` on any GLB, or ask). It's needed for decimation and FBX.
   - Optional: Rojo 7.x (`rojo --version`). Without it, studio-importer gives the manual path.
2. **Design**: invoke game-designer. Show the user the design doc summary and the asset table.
3. **Budget gate**: total the credits from `plan.json` (or `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sloyd-api/scripts/sloyd.py estimate roblox-assets/plan.json`), call `get_credit_balance`, and show `jobs / credits / ~USD / balance`. Wait for an explicit yes. If the balance is short, offer a smaller plan: fewer decor types, or drop variants.
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
