# Candy Climb: design doc

**Pitch.** Hop across giant gumdrops above a chocolate river to reach the cake at the top, and grab wrapped candies to buy sweeter backpacks.

**Genre.** Obby with collectibles and a cosmetic shop (the bundled Rojo kit covers all of it).

## Loop

1. Jump from gumdrop to gumdrop. Each one is a little higher.
2. Grab the wrapped candy over each platform: +1 coin, and it respawns after 12 s.
3. Touch a cupcake every 4 platforms to save your checkpoint.
4. Reach the giant cake: +25 coins, once per session.
5. Spend coins at the candy stall on backpack skins, then run it again to show them off.

## First 30 seconds

You spawn on a pink pad, with the candy stall to your left and a line of gumdrops rising to the right under a golden pastel sky. The first jump is short, and the first candy is right above it. The shop prompt reads "Open shop" as you walk past.

## Progression and economy

| Source | Coins |
|---|---|
| Candy pickup (12 on the course, 12 s respawn) | 1 each |
| Finish | 25 once per session |
| Coin pack (developer product, optional) | 100 |

| Sink | Price |
|---|---|
| Classic Pink backpack | free (starter) |
| Mint Swirl | 15 |
| Choco Fudge | 30 |
| Galaxy Gummy | 60 |

The first skin takes about one run. Galaxy takes three or four runs, or one coin pack. Skins are cosmetic only.

## Course

16 stages. Platforms 10 studs across, 14 studs centre to centre (about 4 studs edge to edge, with up to 6 studs of sideways drift), rising 0.5–2.5 studs per jump. A cupcake checkpoint every 4 stages. A neon chocolate kill floor 12 studs below the start.

## Art direction

- Sloyd style: `Roblox` for props (chunky, saturated, reads on phones), `CozyMobile` for the sky.
- Palette: bubblegum pink `#FF78BE`, mint `#78FFB4`, lemon `#FFDC50`, chocolate `#6E3C23`, cream `#FFF5EB`.
- Shapes: rounded, glossy, no sharp edges. Everything looks edible.

## Assets

| Name | Role | Count | Size (studs) | Triangle budget |
|---|---|---|---|---|
| GumdropPlatform | platform | 12 | 10 across | 3,000 |
| WrappedCandy | collectible | 12 | 2.5 long | 800 |
| CupcakeCheckpoint | checkpoint | 4 | 6 tall | 4,000 |
| LollipopTree | decor | 14 | 16 tall | 3,000 |
| GiantCake | finish | 1 | 12 tall | 12,000 |
| CandyShopStand | shop | 1 | 9 tall | 8,000 |
| CandyBackpack (+3 skins) | cosmetic | 1 per player | 2.5 tall | 2,500 |

On screen at once: about 70k triangles worst case. That's fine on phones.

## Sky

Pastel candy land at golden hour: cotton candy clouds, lollipop hills and a chocolate river on the horizon.

## Cost

7 models × 25 + 3 retextures × 15 + 1 skybox × 25 = **245 credits (about $3.27)**.
