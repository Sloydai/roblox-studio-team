--[[
	Paste into Studio's Command Bar (View -> Command Bar) after importing the FBX files.

	What it does, for every imported asset in Workspace whose name is in ROLES:
	  - moves it into ReplicatedStorage.Assets (where AssetLibrary looks for it)
	  - sets CollisionFidelity per role (scripts can't set this at runtime; the
	    Command Bar runs with plugin permissions, so it can)
	  - anchors it and turns off CanCollide/CanTouch where the role doesn't need them

	luau-scripter regenerates ROLES from the manifest; the names must match GameConfig.Assets.
]]

local ROLES = {
	GumdropPlatform = "platform",
	WrappedCandy = "collectible",
	CupcakeCheckpoint = "checkpoint",
	LollipopTree = "decor",
	GiantCake = "finish",
	CandyShopStand = "shop",
	CandyBackpack = "cosmetic",
	CandyBackpack_Mint = "cosmetic",
	CandyBackpack_Chocolate = "cosmetic",
	CandyBackpack_Galaxy = "cosmetic",
}

-- Platforms players stand on need the real shape; everything else is cheaper as a hull/box.
local FIDELITY = {
	platform = Enum.CollisionFidelity.PreciseConvexDecomposition,
	finish = Enum.CollisionFidelity.PreciseConvexDecomposition,
	checkpoint = Enum.CollisionFidelity.Hull,
	shop = Enum.CollisionFidelity.Hull,
	decor = Enum.CollisionFidelity.Hull,
	collectible = Enum.CollisionFidelity.Box,
	cosmetic = Enum.CollisionFidelity.Box,
}

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ChangeHistoryService = game:GetService("ChangeHistoryService")

local assets = ReplicatedStorage:FindFirstChild("Assets")
if not assets then
	assets = Instance.new("Folder")
	assets.Name = "Assets"
	assets.Parent = ReplicatedStorage
end

local recording = ChangeHistoryService:TryBeginRecording("Setup Sloyd assets")
local moved, missing = {}, {}
for name, role in ROLES do
	local inst = workspace:FindFirstChild(name, true) or assets:FindFirstChild(name)
	if not inst then
		table.insert(missing, name)
		continue
	end
	local parts = inst:IsA("BasePart") and { inst } or {}
	for _, d in inst:GetDescendants() do
		if d:IsA("BasePart") then
			table.insert(parts, d)
		end
	end
	for _, p in parts do
		p.Anchored = role ~= "cosmetic"
		if p:IsA("MeshPart") then
			p.CollisionFidelity = FIDELITY[role]
			p.RenderFidelity = Enum.RenderFidelity.Automatic
		end
	end
	if inst:IsA("Model") and not inst.PrimaryPart then
		inst.PrimaryPart = parts[1]
	end
	inst.Parent = assets
	table.insert(moved, name)
end
if recording then
	ChangeHistoryService:FinishRecording(recording, Enum.FinishRecordingOperation.Commit)
end
print(("[Sloyd] moved %d assets into ReplicatedStorage.Assets"):format(#moved))
if #missing > 0 then
	warn("[Sloyd] not found (import them, or check the names): " .. table.concat(missing, ", "))
end
