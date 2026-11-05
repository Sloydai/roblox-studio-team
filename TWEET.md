# Launch tweet: Roblox Studio Team

Status: copy is final. All media comes from the real Candy Climb run on 2026-11-04 (`examples/candy-climb/`, 11 Sloyd jobs, 245 credits). No mockups. Only the Studio gameplay recording is still to capture.

## Main post (hook)

> Claude now builds Roblox games with custom 3D assets.
>
> One prompt: "obby in a candy world"
> → design doc
> → 7 Sloyd 3D props, auto-fit to Roblox's 20k-tri limit
> → 3 shop skins
> → custom skybox
> → Luau + Rojo place you can press Play on
>
> 🧵👇

Media: video, 9:16 or 16:9, 20–30 s (shot list below).

### Alternate hooks

1. > I typed "obby in a candy world" into Claude Code and got a playable Roblox game. Every 3D model in it was generated, decimated and imported by a team of 7 Claude skills.
2. > Roblox devs: stop searching the Toolbox for props. 7 Claude skills now design your game, generate custom 3D assets with Sloyd, make them Studio-ready and write the Luau.

## Thread

**2/** The team:

```
roblox-studio/
├─ roblox-producer   runs the pipeline, checks the budget
├─ game-designer     idea → design doc + asset list
├─ prop-modeler      Sloyd 3D → <20k tris, studs, FBX
├─ skin-variants     retexture → shop skins
├─ world-backdrop    skybox → Roblox Sky faces
├─ luau-scripter     course, coins, shop, DataStore
└─ studio-importer   Importer settings + Rojo
```

Media: the folder tree as an image, or a screenshot of the skills list in Claude Code.

**3/** The boring parts are done right. Every asset gets a triangle budget up front (784 for the candy, 12k for the cake, never over Roblox's 20k), is scaled to studs, gets a ground pivot, gets textures sized for its studs (2048 → 256 px on pickups), and is re-imported to verify. 10/10 Studio-ready on the first run.

Media: `examples/candy-climb/images/props-sheet.png` with each asset's triangle count as a caption.

**4/** Monetization built in: one backpack, three retextured skins, coin prices, plus Robux coin packs. Purchases are validated on the server and saved in DataStores.

Media: `examples/candy-climb/images/skins-sheet.png` (Classic, Mint 15, Choco 30, Galaxy 60).

**5/** Install:

```
claude plugin marketplace add Sloydai/roblox-studio-team
claude plugin install roblox-studio@sloyd-roblox-studio-team
```

Then: `/roblox-studio:roblox-producer obby in a candy world`

github.com/Sloydai/roblox-studio-team

## Demo video shot list (20–30 s)

| # | Time | Shot | Source |
|---|---|---|---|
| 1 | 0–3 s | Claude Code terminal: type `/roblox-studio:roblox-producer obby in a candy world`, press Enter | screen recording |
| 2 | 3–6 s | Design doc and asset table scroll past; cost line "11 jobs, 245 credits, balance …" and the user typing "yes" | screen recording |
| 3 | 6–10 s | Grid of the 7 real props popping in as each Sloyd job finishes (turntable renders) | `roblox_mesh.py preview` renders of the real exports |
| 4 | 10–12 s | One prop's triangle count ticking from the raw value down to its budget, "Roblox-ready ✓" | the asset's `report.json` numbers |
| 5 | 12–14 s | The four backpack skins side by side | real retexture renders |
| 6 | 14–16 s | Sky cross unfolding into the six faces | `examples/candy-climb/images/sky-cross.png` |
| 7 | 16–19 s | Studio: File → Import with the FBXs, then the Command Bar setup script printing "moved N assets" | Studio screen recording |
| 8 | 19–27 s | Play mode: run and jump the gumdrop course under the candy sky, grab a candy (coin +1), checkpoint cupcake, buy the Galaxy backpack, finish at the cake | Studio screen recording |
| 9 | 27–30 s | End card: "Claude + Sloyd. Roblox games with custom 3D." with the install line and repo link | Sloyd brand template (Poppins, navy `#12234a`, CTA gradient `#45bcff → #03f584`) |

Recording notes:
- Shots 7–8 need Roblox Studio on Windows or macOS and the generated models. The models aren't in the repo, so run `examples/candy-climb/plan.json` with a Sloyd key first (245 credits, see the example README), build the place, import the FBXs, run the Command Bar script, then Play.
- Use **Test → Device → phone** for one Play-mode cut, since most Roblox players are on phones.
- Keep the Claude Code terminal font large (≥18 pt) for the 9:16 crop.

## Media checklist

- [x] `examples/candy-climb/images/renders/*.png`: 7 props + 3 skins, plus `props-sheet.png` and `skins-sheet.png`
- [x] Triangle counts per asset: `examples/candy-climb/run-record.json` and `export/roblox/IMPORT.md`
- [x] `examples/candy-climb/images/sky-cross.png`
- [x] Credits spent: 245 (balance 415 → 170)
- [ ] Studio import + Play-mode recording (shots 7–8), needs Roblox Studio on Windows or macOS
