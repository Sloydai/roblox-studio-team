--!strict
-- Spawns assets by name. Uses the imported model in ReplicatedStorage.Assets when it
-- exists, otherwise a placeholder block, so the game runs before any import.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(script.Parent.GameConfig)

local AssetLibrary = {}

local function assetsFolder(): Folder?
	return ReplicatedStorage:FindFirstChild("Assets") :: Folder?
end

function AssetLibrary.isImported(name: string): boolean
	local folder = assetsFolder()
	return folder ~= nil and folder:FindFirstChild(name) ~= nil
end

local function bounds(inst: PVInstance): (CFrame, Vector3)
	if inst:IsA("Model") then
		return inst:GetBoundingBox()
	end
	local part = inst :: BasePart
	return part.CFrame, part.Size
end

local function placeholder(name: string): BasePart
	local spec = Config.Assets[name]
	local part = Instance.new("Part")
	part.Name = name
	part.Size = if spec then spec.size else Vector3.new(4, 4, 4)
	part.Color = if spec then spec.color else Color3.fromRGB(200, 200, 200)
	part.Material = Enum.Material.SmoothPlastic
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part:SetAttribute("Placeholder", true)
	return part
end

-- Returns a fresh copy of the asset, not yet parented.
function AssetLibrary.spawn(name: string): PVInstance
	local folder = assetsFolder()
	local template = folder and folder:FindFirstChild(name)
	if template == nil or not template:IsA("PVInstance") then
		return placeholder(name)
	end
	local copy = (template :: PVInstance):Clone()
	local spec = Config.Assets[name]
	if copy:IsA("Model") and spec and spec.fitHeight ~= false then
		local _, size = copy:GetBoundingBox()
		if size.Y > 0 then
			copy:ScaleTo(copy:GetScale() * (spec.size.Y / size.Y))
		end
	end
	return copy
end

-- Moves `inst` so the bottom of its bounding box sits on `ground`, whatever its pivot.
function AssetLibrary.placeOnGround(inst: PVInstance, ground: CFrame)
	inst:PivotTo(ground)
	local box, size = bounds(inst)
	local bottom = box.Position.Y - size.Y / 2
	inst:PivotTo(ground + Vector3.new(0, ground.Position.Y - bottom, 0))
end

function AssetLibrary.topY(inst: PVInstance): number
	local box, size = bounds(inst)
	return box.Position.Y + size.Y / 2
end

function AssetLibrary.parts(inst: Instance): { BasePart }
	local list: { BasePart } = {}
	if inst:IsA("BasePart") then
		table.insert(list, inst)
	end
	for _, d in inst:GetDescendants() do
		if d:IsA("BasePart") then
			table.insert(list, d)
		end
	end
	return list
end

-- Physics flags for a role. CollisionFidelity cannot be set from scripts; set it on the
-- imported MeshParts in Studio (studio-importer covers which value to pick).
function AssetLibrary.applyRole(inst: Instance, role: string)
	for _, part in AssetLibrary.parts(inst) do
		part.Anchored = role ~= "cosmetic"
		if role == "platform" or role == "finish" or role == "shop" or role == "checkpoint" then
			part.CanCollide = true
			part.CanTouch = role ~= "shop"
		elseif role == "collectible" then
			part.CanCollide = false
			part.CanTouch = true
			part.CanQuery = false
		elseif role == "cosmetic" then
			part.CanCollide = false
			part.CanTouch = false
			part.CanQuery = false
			part.Massless = true
		else -- decor
			part.CanCollide = true
			part.CanTouch = false
		end
	end
end

return AssetLibrary
