# Candy Climb: the launch demo

The team's run for "obby in a candy world". The tweet's media comes from here.

| Stage | Status |
|---|---|
| game-designer: `roblox-assets/design-doc.md`, `roblox-assets/plan.json` | done |
| prop-modeler, skin-variants, world-backdrop | waiting on credits (245 needed; the key's balance was 0 on 2026-11-04) |
| luau-scripter: `roblox-game/` | done once assets exist (the kit already matches this plan's names and sizes) |
| Studio recording | needs Roblox Studio on Windows or macOS |

## Run it

```bash
cd examples/candy-climb
# In Claude Code:
/roblox-studio:roblox-producer build the plan in roblox-assets/plan.json

# Or without the MCP server (REST fallback, same rules):
python3 ../../scripts/sloyd_api.py estimate roblox-assets/plan.json
python3 ../../scripts/sloyd_api.py run roblox-assets/plan.json --out roblox-assets
python3 ../../scripts/roblox_mesh.py batch roblox-assets/manifest.json
for f in roblox-assets/export/*/*.glb; do n=$(basename "$f" .glb); python3 ../../scripts/roblox_mesh.py preview "$f" --out roblox-assets/previews/$n.png; done
python3 ../../scripts/roblox_sky.py --job roblox-assets/sky/sky_job.json --out roblox-assets/sky   # sky_job.json = get_job output
cp -R ../../templates/rojo-game roblox-game && (cd roblox-game && rojo build default.project.json -o SloydGame.rbxlx)
```
