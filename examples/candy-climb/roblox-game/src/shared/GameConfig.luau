--!strict
-- Single source of truth for the game. luau-scripter rewrites this file from the
-- design doc and the prop-modeler manifest. Every asset name here must match a
-- child of ReplicatedStorage.Assets once imported; until then a coloured block
-- of the same size stands in, so the place is playable from the first build.

export type AssetSpec = {
	size: Vector3, -- studs, used for the placeholder and for fitting imported models
	color: Color3, -- placeholder colour
	role: "platform" | "collectible" | "checkpoint" | "decor" | "finish" | "shop" | "cosmetic",
	fitHeight: boolean?, -- scale imported Models to size.Y (default true)
}

export type Skin = {
	id: string,
	displayName: string,
	asset: string, -- name in ReplicatedStorage.Assets (a retextured variant)
	price: number, -- in-game coins; 0 = free starter
}

local Config = {}

Config.DataStoreName = "SloydGame_v1"
Config.AutosaveSeconds = 120

Config.Assets = {
	GumdropPlatform = { size = Vector3.new(9.96, 2.5, 10.0), color = Color3.fromRGB(255, 120, 190), role = "platform" },
	WrappedCandy = { size = Vector3.new(2.5, 0.96, 0.8), color = Color3.fromRGB(255, 220, 80), role = "collectible" },
	CupcakeCheckpoint = { size = Vector3.new(4.51, 6.0, 4.51), color = Color3.fromRGB(120, 230, 255), role = "checkpoint" },
	LollipopTree = { size = Vector3.new(8.01, 16.0, 8.01), color = Color3.fromRGB(180, 120, 255), role = "decor" },
	GiantCake = { size = Vector3.new(13.71, 12.0, 13.71), color = Color3.fromRGB(255, 245, 235), role = "finish" },
	CandyShopStand = { size = Vector3.new(9.57, 9.0, 8.52), color = Color3.fromRGB(120, 255, 180), role = "shop" },
	CandyBackpack = { size = Vector3.new(1.64, 2.5, 2.06), color = Color3.fromRGB(255, 120, 190), role = "cosmetic" },
} :: { [string]: AssetSpec }

-- Obby course: platforms laid out from the spawn, rising and drifting sideways.
Config.Course = {
	seed = 7,
	stages = 16,
	platform = "GumdropPlatform",
	-- Default character: WalkSpeed 16, JumpHeight 7.2 -> ~0.54 s airtime -> ~8.5 studs of
	-- horizontal travel. Keep the edge-to-edge gap (gap - platform width) at 6 or less.
	gap = 14, -- studs between platform centres
	rise = 2.5, -- max height gained per jump (must stay well under 7.2)
	sideways = 6,
	checkpoint = "CupcakeCheckpoint",
	checkpointEvery = 4,
	finish = "GiantCake",
	finishReward = 25,
}

Config.Collectibles = {
	asset = "WrappedCandy",
	value = 1,
	respawnSeconds = 12,
	hover = 3.5, -- studs above the platform top
}

Config.Decor = {
	{ asset = "LollipopTree", count = 14, minRadius = 30, maxRadius = 90 },
}

Config.KillFloor = { enabled = true, height = -12, color = Color3.fromRGB(110, 60, 35) }

Config.Shop = {
	stand = "CandyShopStand",
	position = Vector3.new(-18, 0, 0),
	item = "CandyBackpack",
	skins = {
		{ id = "Classic", displayName = "Classic Pink", asset = "CandyBackpack", price = 0 },
		{ id = "Mint", displayName = "Mint Swirl", asset = "CandyBackpack_Mint", price = 15 },
		{ id = "Chocolate", displayName = "Choco Fudge", asset = "CandyBackpack_Chocolate", price = 30 },
		{ id = "Galaxy", displayName = "Galaxy Gummy", asset = "CandyBackpack_Galaxy", price = 60 },
	} :: { Skin },
	-- Robux developer products that grant coins. productId 0 = hidden until you create one
	-- (Creator Dashboard -> your experience -> Monetization -> Developer Products).
	coinProducts = {
		{ productId = 0, coins = 100 },
	},
}

-- Fill with the rbxassetid of each uploaded face (see world-backdrop). nil = default sky.
Config.Sky = nil :: { [string]: string }?

return Config
