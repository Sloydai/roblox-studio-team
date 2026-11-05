--!strict
-- Spins and bobs collectibles on the client only, so the server never streams the motion.

local CollectionService = game:GetService("CollectionService")
local RunService = game:GetService("RunService")

type Entry = { inst: PVInstance, base: CFrame, phase: number }
local entries: { [Instance]: Entry } = {}

local function add(inst: Instance)
	if inst:IsA("PVInstance") then
		entries[inst] = { inst = inst, base = inst:GetPivot(), phase = math.random() * math.pi * 2 }
	end
end

CollectionService:GetInstanceAddedSignal("Collectible"):Connect(add)
CollectionService:GetInstanceRemovedSignal("Collectible"):Connect(function(inst)
	entries[inst] = nil
end)
for _, inst in CollectionService:GetTagged("Collectible") do
	add(inst)
end

RunService.RenderStepped:Connect(function()
	local t = os.clock()
	for inst, e in entries do
		if inst.Parent == nil then
			entries[inst] = nil
			continue
		end
		local bob = math.sin(t * 2 + e.phase) * 0.4
		e.inst:PivotTo(e.base * CFrame.new(0, bob, 0) * CFrame.Angles(0, t * 1.5 + e.phase, 0))
	end
end)
