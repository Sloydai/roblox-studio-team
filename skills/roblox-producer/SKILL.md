---
name: roblox-producer
description: Use when the user wants a Roblox game built end to end in one request. Examples are "make me a Roblox obby in a candy world", "build a tycoon with custom models", "turn this idea into a Roblox place" or "be my Roblox studio". Orchestrates the whole Roblox Studio Team with Sloyd (design doc, 3D props under Roblox limits, shop skins, skybox, Luau and Rojo) and ends in a playable place plus importable assets. For a single asset or one step, use the specific role skill instead.
---

# Roblox Producer

> **Script paths:** `<skills>` below means the folder this skill is installed in, the parent of this `SKILL.md`'s folder (for example `.agents/skills` or `.claude/skills`). All Roblox Studio Team skills sit side by side there. On Windows, use `python` instead of `python3`.

You run a small studio of six specialist skills, with sloyd-api as shared plumbing. Your job is sequencing, budget and hand-offs. Each specialist owns its files; you check each hand-off before starting the next stage.

Load the sloyd-api skill first (credentials, credits, job loop, errors), and read `<skills>/studio-importer/references/roblox-reference.md` (Roblox limits).

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

1. **Preflight** (no credits spent). Run this from the user's project folder:

   ```bash
   python3 <skills>/roblox-producer/scripts/check_setup.py
   ```

   It checks Python, that all 8 skills are installed, the Sloyd key and credits, Blender and (optionally) Rojo, and prints the exact fix for anything missing. It never prints the key.
   - If the key line says `[missing]`, stop and tell the user to run `python3 <skills>/sloyd-api/scripts/sloyd.py setup` **themselves, in their own terminal** (it asks for the secret with hidden input). Never ask for the secret in chat.
   - If Blender is missing, give them the download link from the output and wait. Blender is needed for every model.
   - Rojo doesn't need installing: `build_place.py` downloads it when it builds the game. An installed Rojo is only needed for live sync.
   - Sloyd calls: use the Sloyd MCP tools if they're connected. If not, run the same tool with `python3 <skills>/sloyd-api/scripts/sloyd.py tool <tool_name> '<json args>'`, and batches with `sloyd.py run plan.json`.
2. **Design**: invoke game-designer. Show the user the design doc summary and the asset table.
3. **Budget gate**: total the credits from `plan.json` (or `python3 <skills>/sloyd-api/scripts/sloyd.py estimate roblox-assets/plan.json`), call `get_credit_balance`, and show `jobs / credits / ~USD / balance`. Wait for an explicit yes. If the balance is short, offer a smaller plan: fewer decor types, or drop variants.
4. **Assets**: invoke prop-modeler. Then skin-variants and world-backdrop.
5. **Gate**: every asset in `manifest.json` has `export.ready: true`. If not, fix it with prop-modeler (regenerate with a lower `targetFaceCount`, or re-run `roblox_mesh.py process` with a lower `--target-tris`). Never hand a model over 20,000 triangles to the importer.
6. **Code**: invoke luau-scripter. Gate: `build_place.py` writes `roblox-game/SloydGame.rbxlx`; if `luau-lsp` is installed, `luau-lsp analyze` has no errors.
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
